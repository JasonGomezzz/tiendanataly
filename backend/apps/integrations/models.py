from django.db import models


class WebhookOutbox(models.Model):
    """Cola de eventos salientes (n8n → avisos por WhatsApp). Patrón outbox: se escribe en la
    misma transacción que el cambio y un worker lo entrega con reintentos."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ENVIADO = "enviado", "Enviado"
        FALLIDO = "fallido", "Fallido"

    evento = models.CharField(max_length=60, db_index=True)
    payload = models.JSONField(default=dict)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    intentos = models.PositiveSmallIntegerField(default=0)
    ultimo_error = models.CharField(max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    enviado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["creado_en"]
        verbose_name = "evento saliente"
        verbose_name_plural = "eventos salientes"
