from django.db import IntegrityError, transaction

from apps.payments.models import Payment

from .base import PaymentProvider


class ManualYapePlinProvider(PaymentProvider):
    """Pago por Yape/Plin a la cuenta de la tienda con captura de comprobante.
    La administradora lo verifica a mano antes de pasar el pedido a PAGADO."""

    name = Payment.Proveedor.MANUAL

    def create_payment(self, order, *, idempotency_key, metodo=Payment.Metodo.YAPE, comprobante=None, **kwargs):
        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
        amount = order.amount_due()
        if amount <= 0:
            raise ValueError("El pedido no tiene nada por pagar.")
        try:
            with transaction.atomic():
                return Payment.objects.create(
                    pedido=order,
                    proveedor=self.name,
                    metodo=metodo,
                    monto=amount,
                    es_adelanto=order.tipo_venta == "por_encargo" and order.estado == "PENDIENTE_PAGO",
                    estado=Payment.Estado.EN_REVISION if comprobante else Payment.Estado.PENDIENTE,
                    idempotency_key=idempotency_key,
                    comprobante=comprobante or "",
                )
        except IntegrityError:
            return Payment.objects.get(idempotency_key=idempotency_key)
