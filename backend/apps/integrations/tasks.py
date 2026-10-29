import hashlib
import hmac
import json
import urllib.request

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import WebhookOutbox

MAX_ATTEMPTS = 8


def _sign(body: bytes) -> str:
    return hmac.new(settings.N8N_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


@shared_task
def flush_outbox():
    """Entrega eventos pendientes a n8n. Sin N8N_WEBHOOK_URL no hace nada (fase 3 activa el envío)."""
    if not settings.N8N_WEBHOOK_URL:
        return 0
    sent = 0
    for event in WebhookOutbox.objects.filter(estado=WebhookOutbox.Estado.PENDIENTE)[:50]:
        body = json.dumps({"evento": event.evento, "payload": event.payload, "id": event.pk}).encode()
        req = urllib.request.Request(
            settings.N8N_WEBHOOK_URL,
            data=body,
            headers={"Content-Type": "application/json", "X-Signature": _sign(body)},
            method="POST",
        )
        event.intentos += 1
        try:
            with urllib.request.urlopen(req, timeout=10):
                event.estado = WebhookOutbox.Estado.ENVIADO
                event.enviado_en = timezone.now()
                sent += 1
        except Exception as exc:  # noqa: BLE001 - se registra y se reintenta
            event.ultimo_error = str(exc)[:255]
            if event.intentos >= MAX_ATTEMPTS:
                event.estado = WebhookOutbox.Estado.FALLIDO
        event.save()
    return sent
