import time
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.payments.models import Payment

from .base import PaymentProvider
from .culqi_client import CulqiClient, CulqiError

SAFE_KEYS = ("id", "object", "amount", "currency_code", "creation_date", "state", "order_number", "outcome")
SAFE_OUTCOME = ("type", "code", "merchant_message", "user_message")
SUCCESS_OUTCOMES = {"venta_exitosa"}
ORDER_TTL_SECONDS = 60 * 60 * 24  # una orden de pago Culqi vence en 24 h


def to_cents(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).to_integral_value())


def sanitize(resp: dict) -> dict:
    """Guarda solo lo necesario para auditoría. Nunca datos de tarjeta, tokens ni metadatos."""
    out = {k: resp[k] for k in SAFE_KEYS if k in resp}
    if isinstance(out.get("outcome"), dict):
        out["outcome"] = {k: out["outcome"][k] for k in SAFE_OUTCOME if k in out["outcome"]}
    return out


def charge_succeeded(charge: dict) -> bool:
    outcome = charge.get("outcome") or {}
    return outcome.get("type") in SUCCESS_OUTCOMES


class CulqiProvider(PaymentProvider):
    """Tarjetas (y billeteras vía orden de pago) con Culqi.

    - El servidor nunca recibe datos de tarjeta: solo el token que genera Culqi Checkout (SAQ-A).
    - El monto sale del pedido en el servidor, jamás del cliente.
    - Cada intento lleva su idempotency_key: reintentar no cobra dos veces.
    """

    name = Payment.Proveedor.CULQI

    def __init__(self, client=None):
        self.client = client or CulqiClient()

    def _new_payment(self, order, key, metodo):
        amount = order.amount_due()
        if amount <= 0:
            raise ValueError("El pedido no tiene nada por pagar.")
        return Payment.objects.create(
            pedido=order, proveedor=self.name, metodo=metodo, monto=amount, idempotency_key=key,
            es_adelanto=order.tipo_venta == "por_encargo" and order.estado == "PENDIENTE_PAGO",
        )

    def create_payment(self, order, *, idempotency_key, token_id=None, email="", **kwargs):
        """Cobra con tarjeta usando el token de Culqi Checkout."""
        from apps.payments import services

        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
        if not token_id:
            raise ValueError("Falta el token de pago.")
        try:
            with transaction.atomic():
                payment = self._new_payment(order, idempotency_key, Payment.Metodo.TARJETA)
        except IntegrityError:  # dos envíos simultáneos con la misma clave
            return Payment.objects.get(idempotency_key=idempotency_key)

        try:
            charge = self.client.create_charge({
                "amount": to_cents(payment.monto),
                "currency_code": "PEN",
                "email": email or order.cliente.email or "sin-correo@tienda.invalid",
                "source_id": token_id,
                "description": f"Pedido #{order.pk}",
                "metadata": {"pedido": str(order.pk), "pago": str(payment.pk)},
            })
        except CulqiError as exc:
            payment.estado = Payment.Estado.RECHAZADO
            payment.nota = exc.user_message[:255]
            payment.payload = sanitize(exc.body)
            payment.save()
            return payment

        payment.external_id = charge.get("id", "")
        payment.payload = sanitize(charge)
        if charge_succeeded(charge):
            payment.save()
            return services.approve_payment(payment)
        payment.estado = Payment.Estado.RECHAZADO
        payment.nota = str((charge.get("outcome") or {}).get("user_message") or "Pago no aprobado.")[:255]
        payment.save()
        return payment

    def create_order(self, order, *, idempotency_key, email="", **kwargs):
        """Crea una orden de pago de Culqi (billeteras, PagoEfectivo): se confirma por webhook order.status.changed."""
        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
        try:
            with transaction.atomic():
                payment = self._new_payment(order, idempotency_key, Payment.Metodo.OTRO)
        except IntegrityError:
            return Payment.objects.get(idempotency_key=idempotency_key)
        first, _, last = (order.cliente.nombre or "Cliente").partition(" ")
        resp = self.client.create_order({
            "amount": to_cents(payment.monto),
            "currency_code": "PEN",
            "description": f"Pedido #{order.pk}",
            "order_number": f"P{order.pk}-{payment.pk}",
            "client_details": {
                "first_name": first, "last_name": last or first,
                "email": email or order.cliente.email or "sin-correo@tienda.invalid",
                "phone_number": order.cliente.telefono,
            },
            "expiration_date": int(time.time()) + ORDER_TTL_SECONDS,
            "confirm": False,
        })
        payment.external_id = resp.get("id", "")
        payment.payload = sanitize(resp)
        payment.save()
        return payment
