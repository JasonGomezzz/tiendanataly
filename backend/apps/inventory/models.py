from django.conf import settings
from django.db import models
from django.db.models import Q


class StockReservation(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        CONSUMIDA = "consumida", "Consumida (vendida)"
        LIBERADA = "liberada", "Liberada"

    variante = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT, related_name="reservas")
    pedido = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.CASCADE, related_name="reservas")
    cantidad = models.PositiveIntegerField()
    expira_en = models.DateTimeField(db_index=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVA, db_index=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "reserva de stock"
        verbose_name_plural = "reservas de stock"
        constraints = [models.CheckConstraint(condition=Q(cantidad__gt=0), name="reserva_cantidad_positiva")]

    def __str__(self):
        return f"{self.cantidad} × {self.variante} ({self.estado})"


class InventoryMovement(models.Model):
    """Libro de movimientos. El stock siempre se puede reconstruir sumando los deltas."""

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        VENTA = "venta", "Venta"
        RESERVA = "reserva", "Reserva"
        LIBERACION = "liberacion", "Liberación"
        AJUSTE = "ajuste", "Ajuste"

    variante = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices, db_index=True)
    # Efecto sobre stock_disponible (físico) y stock_reservado.
    delta_disponible = models.IntegerField(default=0)
    delta_reservado = models.IntegerField(default=0)
    disponible_resultante = models.PositiveIntegerField()
    reservado_resultante = models.PositiveIntegerField()
    motivo = models.CharField(max_length=200, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    pedido = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reserva = models.ForeignKey(StockReservation, null=True, blank=True, on_delete=models.SET_NULL, related_name="movimientos")
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en", "-id"]
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"

    @property
    def cantidad(self):
        return abs(self.delta_disponible or self.delta_reservado)

    def __str__(self):
        return f"{self.tipo} {self.variante_id} {self.delta_disponible:+d}/{self.delta_reservado:+d}"
