"""Máquina de estados del pedido y sus efectos sobre el stock."""
from django.db import transaction
from django.utils import timezone

from apps.inventory import services as stock
from apps.inventory.models import StockReservation
from apps.integrations.services import enqueue

from .models import Order, OrderStatusHistory

E = Order.Estado

ALLOWED_TRANSITIONS = {
    E.PENDIENTE_PAGO: {E.PAGADO, E.CANCELADO, E.EXPIRADO},
    # Un pago por Yape/Plin puede aprobarse tarde, cuando la reserva ya venció.
    E.EXPIRADO: {E.PAGADO},
    E.PAGADO: {E.COMPRADO, E.EN_LIMA, E.ENTREGADO, E.CANCELADO},
    E.COMPRADO: {E.EN_CAMINO, E.CANCELADO},
    E.EN_CAMINO: {E.EN_LIMA},
    E.EN_LIMA: {E.ENTREGADO},
    E.ENTREGADO: set(),
    E.CANCELADO: set(),
}


class OrderError(Exception):
    pass


def _confirm_stock(order):
    """Convierte las reservas del pedido en venta. Si ya vencieron, intenta reservar de nuevo."""
    if order.tipo_venta == "por_encargo":
        return
    active = list(order.reservas.filter(estado=StockReservation.Estado.ACTIVA))
    try:
        if not active:
            items = [(i.variante, i.cantidad) for i in order.items.select_related("variante")]
            active = stock.reserve_many(items, order=order, minutes=1)
        for reservation in active:
            stock.consume(reservation)
    except stock.StockError as exc:
        raise OrderError(f"No se puede confirmar el pago: {exc}. Corresponde reembolsar.") from exc


def _free_stock(order, anterior):
    for reservation in order.reservas.filter(estado=StockReservation.Estado.ACTIVA):
        stock.release(reservation, f"Pedido {order.pk} {order.estado.lower()}")
    # Cancelar un pedido ya pagado devuelve las unidades al inventario.
    if anterior == E.PAGADO and order.tipo_venta == "stock_local":
        for item in order.items.select_related("variante"):
            stock.add_stock(item.variante, item.cantidad, f"Cancelación del pedido {order.pk}")


@transaction.atomic
def transition(order, nuevo, user=None, nota=""):
    """Cambia el estado validando la transición, ajusta stock y deja historial + evento para n8n."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    anterior = order.estado
    if nuevo not in ALLOWED_TRANSITIONS.get(anterior, set()):
        raise OrderError(f"No se puede pasar de {anterior} a {nuevo}.")

    order.estado = nuevo
    if nuevo == E.PAGADO:
        _confirm_stock(order)
        order.expira_en = None
    elif nuevo in (E.CANCELADO, E.EXPIRADO):
        _free_stock(order, anterior)
    order.save()

    OrderStatusHistory.objects.create(pedido=order, estado_anterior=anterior, estado_nuevo=nuevo, usuario=user, nota=nota)
    enqueue("order.status_changed", {
        "pedido": order.pk, "token": str(order.public_token), "anterior": anterior, "nuevo": nuevo,
        "cliente": order.cliente.nombre, "telefono": order.cliente.telefono, "total": str(order.total_pen),
        "tipo_venta": order.tipo_venta, "saldo_pendiente": str(order.saldo_pendiente),
    })
    return order


def expire_pending_orders(now=None):
    """Pasa a EXPIRADO los pedidos sin pagar cuya reserva venció y libera su stock.

    Un pedido con un comprobante en revisión no expira: espera la verificación manual.
    """
    from apps.payments.models import Payment

    now = now or timezone.now()
    candidates = (
        Order.objects.filter(estado=E.PENDIENTE_PAGO, expira_en__lte=now)
        .exclude(pagos__estado=Payment.Estado.EN_REVISION)
        .values_list("pk", flat=True)
    )
    expired = 0
    for pk in list(candidates):
        try:
            transition(Order.objects.get(pk=pk), E.EXPIRADO, nota="Reserva vencida sin pago")
            expired += 1
        except OrderError:
            continue
    return expired
