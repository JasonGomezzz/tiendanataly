from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class StoreSettings(models.Model):
    """Configuración única de la tienda (siempre pk=1)."""

    nombre_tienda = models.CharField(max_length=120, default="Tienda Nataly")
    whatsapp = models.CharField("WhatsApp para pedidos", max_length=20, blank=True, help_text="Con código de país, sin +. Ej: 51999999999")
    aviso_legal = models.CharField(
        max_length=255,
        default="Tienda independiente de importación, no afiliada a Victoria's Secret.",
    )

    # Datos del proveedor (Libro de Reclamaciones, comprobantes). Completar cuando se confirme RUC/persona natural.
    razon_social = models.CharField(max_length=160, blank=True)
    ruc = models.CharField(max_length=11, blank=True)
    direccion_fiscal = models.CharField(max_length=255, blank=True)

    # Precios
    costo_envio_default = models.DecimalField("costo de envío (S/)", max_digits=8, decimal_places=2, default=Decimal("0"))
    envio_estimado_usd = models.DecimalField("envío estimado por producto (US$)", max_digits=8, decimal_places=2, default=Decimal("0"))
    impuestos_estimados_pct = models.DecimalField("impuestos estimados (%)", max_digits=5, decimal_places=2, default=Decimal("0"))
    margen_default = models.DecimalField("margen por defecto (S/)", max_digits=8, decimal_places=2, default=Decimal("0"))
    pct_comision = models.DecimalField(
        "comisión de pasarela (%)", max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        help_text="Se incorpora al precio para no perder ganancia. Aprox. 3.3% a 4.2% + IGV; confirmar con el contrato.",
    )
    redondeo_multiplo = models.PositiveSmallIntegerField("redondear a múltiplos de (S/)", default=5)

    # Pre-order y reservas
    pct_adelanto = models.DecimalField(
        "% de adelanto en pedidos por encargo", max_digits=5, decimal_places=2, default=Decimal("50"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    minutos_reserva = models.PositiveSmallIntegerField("minutos que se reserva una unidad", default=15)

    # Pagos manuales
    yape_numero = models.CharField(max_length=20, blank=True)
    yape_titular = models.CharField(max_length=120, blank=True)
    plin_numero = models.CharField(max_length=20, blank=True)
    plin_titular = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "configuración de la tienda"
        verbose_name_plural = "configuración de la tienda"

    def __str__(self):
        return self.nombre_tienda

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"whatsapp": settings.STORE_WHATSAPP, "nombre_tienda": settings.STORE_NAME})
        return obj


class ExchangeRate(models.Model):
    usd_pen = models.DecimalField("S/ por US$ 1", max_digits=7, decimal_places=4, validators=[MinValueValidator(Decimal("0.0001"))])
    vigente_desde = models.DateField(default=timezone.localdate)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-vigente_desde", "-id"]
        verbose_name = "tipo de cambio"
        verbose_name_plural = "tipos de cambio"

    def __str__(self):
        return f"{self.usd_pen} ({self.vigente_desde})"

    @classmethod
    def current(cls, on=None):
        on = on or timezone.localdate()
        return cls.objects.filter(vigente_desde__lte=on).first()


class AuditLog(models.Model):
    """Registro inmutable de acciones hechas en el admin."""

    class Accion(models.TextChoices):
        CREAR = "crear", "Crear"
        EDITAR = "editar", "Editar"
        ELIMINAR = "eliminar", "Eliminar"
        ACCION = "accion", "Acción"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    accion = models.CharField(max_length=10, choices=Accion.choices)
    modelo = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=64, blank=True)
    objeto_repr = models.CharField(max_length=255, blank=True)
    cambios = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"

    def __str__(self):
        return f"{self.creado_en:%Y-%m-%d %H:%M} {self.usuario_id} {self.accion} {self.modelo}"
