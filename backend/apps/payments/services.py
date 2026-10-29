from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.orders import services as order_services
from apps.orders.models import Order

from .models import Payment


class PaymentError(Exception):
    pass


@transaction.atomic
def approve_payment(payment, user=None):
    """Aprueba un pago en revisión y, si cubre lo que hay que cobrar, pasa el pedido a PAGADO."""
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.estado not in (Payment.Estado.EN_REVISION, Payment.Estado.PENDIENTE):
        raise PaymentError("Este pago ya fue procesado.")
    payment.estado = Payment.Estado.APROBADO
    payment.revisado_por = user
    payment.revisado_en = timezone.now()
    payment.save()

    order = Order.objects.select_for_update().get(pk=payment.pedido_id)
    cobrado = order.pagos.filter(estado=Payment.Estado.APROBADO).aggregate(t=Sum("monto"))["t"] or 0
    if cobrado >= order.monto_a_cobrar and order.estado in (Order.Estado.PENDIENTE_PAGO, Order.Estado.EXPIRADO):
        try:
            order_services.transition(order, Order.Estado.PAGADO, user=user, nota=f"Pago {payment.pk} aprobado")
        except order_services.OrderError as exc:
            raise PaymentError(str(exc)) from exc
    return payment


@transaction.atomic
def reject_payment(payment, user=None, nota=""):
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.estado not in (Payment.Estado.EN_REVISION, Payment.Estado.PENDIENTE):
        raise PaymentError("Este pago ya fue procesado.")
    payment.estado = Payment.Estado.RECHAZADO
    payment.nota = nota[:255]
    payment.revisado_por = user
    payment.revisado_en = timezone.now()
    payment.save()
    return payment
