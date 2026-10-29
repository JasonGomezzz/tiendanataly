from decimal import Decimal

from django.db import models


class ShippingZone(models.Model):
    class Metodo(models.TextChoices):
        DELIVERY_LIMA = "delivery_lima", "Delivery en Lima"
        RECOJO = "recojo", "Recojo en punto"
        COURIER_PROVINCIA = "courier_provincia", "Courier a provincias"

    nombre = models.CharField(max_length=100)
    metodo = models.CharField(max_length=20, choices=Metodo.choices)
    costo = models.DecimalField("costo (S/)", max_digits=8, decimal_places=2, default=Decimal("0"))
    cobertura = models.TextField(blank=True, help_text="Distritos o departamentos cubiertos, uno por línea.")
    courier = models.CharField(max_length=80, blank=True)
    instrucciones = models.TextField(blank=True, help_text="Ej: dirección del punto de recojo.")
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "zona de envío"
        verbose_name_plural = "zonas de envío"

    def __str__(self):
        return f"{self.nombre} (S/ {self.costo})"
