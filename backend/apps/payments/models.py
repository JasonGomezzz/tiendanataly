from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.validators import uuid_upload_path, validate_image_file


class Payment(models.Model):
    class Proveedor(models.TextChoices):
        MANUAL = "manual_yape_plin", "Yape/Plin manual"
        CULQI = "culqi", "Culqi"

    class Metodo(models.TextChoices):
        YAPE = "yape", "Yape"
        PLIN = "plin", "Plin"
        TARJETA = "tarjeta", "Tarjeta"
        TRANSFERENCIA = "transferencia", "Transferencia bancaria"
        OTRO = "otro", "Otro"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_REVISION = "en_revision", "Comprobante en revisión"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        EXPIRADO = "expirado", "Expirado"

    pedido = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="pagos")
    proveedor = models.CharField(max_length=20, choices=Proveedor.choices)
    metodo = models.CharField(max_length=16, choices=Metodo.choices, default=Metodo.OTRO)
    external_id = models.CharField("id en la pasarela", max_length=100, blank=True, db_index=True)
    # El monto lo calcula el servidor a partir del pedido; nunca se acepta el del cliente.
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=3, default="PEN")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    es_adelanto = models.BooleanField(default=False)
    idempotency_key = models.CharField(max_length=80, unique=True)
    comprobante = models.ImageField(upload_to=uuid_upload_path("comprobantes"), validators=[validate_image_file], blank=True)
    payload = models.JSONField("datos de la pasarela (sin datos sensibles)", default=dict, blank=True)
    nota = models.CharField(max_length=255, blank=True)
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    revisado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "pago"

    def __str__(self):
        return f"Pago {self.pk} · {self.monto} {self.moneda} · {self.estado}"


class PaymentEvent(models.Model):
    """Evento crudo recibido de una pasarela (auditoría e idempotencia de webhooks)."""

    proveedor = models.CharField(max_length=20)
    event_id = models.CharField(max_length=100)
    tipo = models.CharField(max_length=60, blank=True)
    payload = models.JSONField(default=dict)
    procesado = models.BooleanField(default=False)
    recibido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recibido_en"]
        constraints = [models.UniqueConstraint(fields=["proveedor", "event_id"], name="evento_unico_por_proveedor")]
        verbose_name = "evento de pago"
        verbose_name_plural = "eventos de pago"


class BankAccount(models.Model):
    """Cuenta de la tienda para recibir transferencias. Se muestra a la clienta al pagar."""

    class Banco(models.TextChoices):
        BCP = "bcp", "BCP"
        INTERBANK = "interbank", "Interbank"
        BBVA = "bbva", "BBVA"
        SCOTIABANK = "scotiabank", "Scotiabank"
        OTRO = "otro", "Otro"

    banco = models.CharField(max_length=12, choices=Banco.choices)
    etiqueta = models.CharField(max_length=60, blank=True, help_text="Ej: Cuenta de ahorros soles")
    numero = models.CharField("número de cuenta", max_length=30)
    cci = models.CharField("CCI (interbancario)", max_length=30, blank=True)
    titular = models.CharField(max_length=120, blank=True)
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "cuenta bancaria"
        verbose_name_plural = "cuentas bancarias"

    def __str__(self):
        return f"{self.get_banco_display()} {self.numero}"
