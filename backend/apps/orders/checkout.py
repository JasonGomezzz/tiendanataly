"""Checkout: convierte el carrito en un pedido reservando el stock de forma atómica.

Todos los montos se calculan aquí con datos de la base; el cliente nunca envía precios.
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Consent, Customer
from apps.catalog.models import Product
from apps.core.models import StoreSettings
from apps.integrations.services import enqueue
from apps.inventory import services as stock
from apps.shipping.models import ShippingZone

from .models import Order, OrderItem, OrderStatusHistory

CENT = Decimal("0.01")
PREORDER_HOURS = 24  # un pedido por encargo sin adelanto vence a las 24 h


class CheckoutError(Exception):
    def __init__(self, message, *, status=400, code="checkout"):
        super().__init__(message)
        self.status = status
        self.code = code


def _customer_for(user, data):
    if user is not None and user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(user=user, defaults={"nombre": data["nombre"], "telefono": data["telefono"], "email": user.email})
        Customer.objects.filter(pk=customer.pk).update(nombre=data["nombre"], telefono=data["telefono"])
        customer.refresh_from_db()
        return customer
    return Customer.objects.create(nombre=data["nombre"], telefono=data["telefono"], email=data.get("email", ""))


def _record_consents(customer, data, ip):
    kinds = [Consent.Tipo.PRIVACIDAD, Consent.Tipo.TERMINOS]
    if data.get("acepta_marketing"):
        kinds.append(Consent.Tipo.MARKETING)
    for kind in kinds:
        Consent.objects.create(customer=customer, tipo=kind, ip=ip)


@transaction.atomic
def create_order_from_cart(cart, data, *, user=None, ip=None):
    items = list(cart.items.select_related("variante__producto").order_by("variante_id")) if cart else []
    if not items:
        raise CheckoutError("Tu bolsa está vacía.")

    lines = []
    for it in items:
        v, p = it.variante, it.variante.producto
        if not v.activo or p.estado not in (Product.Estado.PUBLICADO, Product.Estado.AGOTADO) or not p.precio_venta_pen:
            raise CheckoutError(f"«{p.nombre}» ya no está disponible. Quítalo de tu bolsa.", status=409, code="no_disponible")
        lines.append((v, p, it.cantidad, p.precio_venta_pen))

    kinds = {p.tipo_venta for _, p, _, _ in lines}
    if len(kinds) > 1:
        raise CheckoutError("No se pueden mezclar productos en stock con productos por encargo en un mismo pedido.")
    tipo_venta = kinds.pop()

    zone = ShippingZone.objects.filter(pk=data["zona_id"], activa=True, metodo=data["metodo_entrega"]).first()
    if zone is None:
        raise CheckoutError("La zona de envío elegida no es válida.")

    cfg = StoreSettings.load()
    subtotal = sum((price * qty for _, _, qty, price in lines), Decimal("0"))
    envio = zone.costo
    total = (subtotal + envio).quantize(CENT)
    if tipo_venta == "por_encargo":
        adelanto = (total * cfg.pct_adelanto / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
        saldo = total - adelanto
        expira = timezone.now() + timedelta(hours=PREORDER_HOURS)
    else:
        adelanto, saldo = Decimal("0"), Decimal("0")
        expira = timezone.now() + timedelta(minutes=cfg.minutos_reserva)

    customer = _customer_for(user, data)
    _record_consents(customer, data, ip)

    order = Order.objects.create(
        cliente=customer, tipo_venta=tipo_venta, subtotal_pen=subtotal, envio_pen=envio, total_pen=total,
        adelanto_pen=adelanto, saldo_pen=saldo, metodo_entrega=data["metodo_entrega"], zona_envio=zone,
        direccion_entrega=data.get("direccion") or {}, notas=data.get("notas", ""),
        doc_tipo=data.get("doc_tipo", ""), doc_numero=data.get("doc_numero", ""), expira_en=expira,
    )
    OrderItem.objects.bulk_create([
        OrderItem(pedido=order, variante=v, nombre_snapshot=str(v) if v.atributo != "unico" else p.nombre, sku_snapshot=v.sku, precio_unitario=price, cantidad=qty)
        for v, p, qty, price in lines
    ])

    if tipo_venta == "stock_local":
        try:
            stock.reserve_many([(v, qty) for v, _, qty, _ in lines], order=order, minutes=cfg.minutos_reserva)
        except stock.InsufficientStock as exc:
            raise CheckoutError(str(exc), status=409, code="sin_stock") from exc
        except stock.StockError as exc:
            raise CheckoutError(str(exc), status=409, code="no_disponible") from exc

    OrderStatusHistory.objects.create(pedido=order, estado_anterior="", estado_nuevo=Order.Estado.PENDIENTE_PAGO, nota="Pedido creado")
    enqueue("order.created", {"pedido": order.pk, "token": str(order.public_token), "total": str(total), "tipo_venta": tipo_venta})
    cart.items.all().delete()
    return order
