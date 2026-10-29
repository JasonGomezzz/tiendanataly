from .models import WebhookOutbox


def enqueue(evento, payload):
    """Encola un evento para n8n. Se llama dentro de la transacción que cambia el dato."""
    return WebhookOutbox.objects.create(evento=evento, payload=payload)
