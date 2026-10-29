"""Webhooks de Culqi.

Seguridad: aunque el endpoint exige un secreto en la URL (y Basic Auth si está configurada), NO se
confía en el cuerpo del evento. Para marcar un pago como aprobado se consulta a Culqi el estado real
del cargo/orden, se compara el monto y la moneda con lo que el servidor esperaba y recién entonces se
aprueba. Un evento falso solo provoca una consulta que no confirma nada.

Idempotencia: cada evento se guarda una sola vez (proveedor + id). Reprocesar el mismo evento no
duplica pagos ni cambios de estado.
"""
import json
import logging

from django.db import IntegrityError, transaction

from . import services
from .models import Payment, PaymentEvent
from .providers.culqi import charge_succeeded, sanitize, to_cents
from .providers.culqi_client import CulqiClient, CulqiError

logger = logging.getLogger(__name__)

PROVIDER = "culqi"
ORDER_PAID = {"paid", "pagado"}
ORDER_DEAD = {"expired", "expirado", "canceled", "cancelled", "deleted"}


class InvalidEvent(Exception):
    pass


def _data(event):
    data = event.get("data")
    if isinstance(data, str):  # Culqi puede enviar `data` como texto JSON
        try:
            data = json.loads(data)
        except ValueError:
            raise InvalidEvent("data no es JSON")
    if not isinstance(data, dict) or not data.get("id"):
        raise InvalidEvent("evento sin data.id")
    return data


def _payment_for(external_id, real):
    payment = Payment.objects.filter(proveedor=PROVIDER, external_id=external_id).first()
    if payment is None:
        pago_id = (real.get("metadata") or {}).get("pago")
        if pago_id and str(pago_id).isdigit():
            payment = Payment.objects.filter(proveedor=PROVIDER, pk=int(pago_id)).first()
    return payment


def _amount_matches(payment, real):
    return int(real.get("amount", -1)) == to_cents(payment.monto) and real.get("currency_code", "PEN") == "PEN"


def _handle_charge(data, client):
    real = client.get_charge(data["id"])  # estado REAL, no el del evento
    payment = _payment_for(data["id"], real)
    if payment is None:
        return "sin_pago_asociado"
    if payment.estado == Payment.Estado.APROBADO:
        return "ya_aprobado"
    if not charge_succeeded(real):
        return "no_exitoso"
    if not _amount_matches(payment, real):
        logger.error("Culqi: monto/moneda no coinciden para el pago %s", payment.pk)
        return "monto_no_coincide"
    payment.external_id = real.get("id", payment.external_id)
    payment.payload = sanitize(real)
    payment.save()
    services.approve_payment(payment)
    return "aprobado"


def _handle_order(data, client):
    real = client.get_order(data["id"])
    payment = _payment_for(data["id"], real)
    if payment is None:
        return "sin_pago_asociado"
    state = str(real.get("state", "")).lower()
    if state in ORDER_PAID:
        if payment.estado == Payment.Estado.APROBADO:
            return "ya_aprobado"
        if not _amount_matches(payment, real):
            logger.error("Culqi: monto/moneda de la orden no coinciden para el pago %s", payment.pk)
            return "monto_no_coincide"
        payment.payload = sanitize(real)
        payment.save()
        services.approve_payment(payment)
        return "aprobado"
    if state in ORDER_DEAD and payment.estado in (Payment.Estado.PENDIENTE, Payment.Estado.EN_REVISION):
        payment.estado = Payment.Estado.EXPIRADO
        payment.save(update_fields=["estado", "actualizado_en"])
        return "expirado"
    return "sin_cambios"


def process_event(event, client=None):
    """Procesa un evento de Culqi de forma idempotente. Devuelve un texto con el resultado."""
    client = client or CulqiClient()
    event_id = str(event.get("id") or "")
    if not event_id:
        raise InvalidEvent("evento sin id")
    kind = str(event.get("type") or "")
    data = _data(event)

    try:
        with transaction.atomic():
            record = PaymentEvent.objects.create(proveedor=PROVIDER, event_id=event_id, tipo=kind, payload=event if len(json.dumps(event)) < 20000 else {})
    except IntegrityError:
        record = PaymentEvent.objects.get(proveedor=PROVIDER, event_id=event_id)
        if record.procesado:
            return "duplicado"

    try:
        if kind.startswith("charge."):
            result = _handle_charge(data, client)
        elif kind.startswith("order."):
            result = _handle_order(data, client)
        else:
            result = "ignorado"
    except services.PaymentError as exc:
        # El pago se aprobó pero el pedido no pudo confirmarse (p. ej. sin stock): queda para revisión manual.
        logger.error("Culqi: pago aprobado sin poder confirmar el pedido: %s", exc)
        result = "requiere_revision"
    except CulqiError:
        raise  # se responde 5xx para que Culqi reintente; el evento queda sin procesar

    record.procesado = True
    record.save(update_fields=["procesado"])
    return result
