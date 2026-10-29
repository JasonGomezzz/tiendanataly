import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q


class Order(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE_PAGO = "PENDIENTE_PAGO", "Pendiente de pago"
        PAGADO = "PAGADO", "Pagado"
        COMPRADO = "COMPRADO", "Comprado en EE. UU."
        EN_CAMINO = "EN_CAMINO", "En camino"
        EN_LIMA = "EN_LIMA", "En Lima"
        ENTREGADO = "ENTREGADO", "Entregado"
        CANCELADO = "CANCELADO", "Cancelado"
        EXPIRADO = "EXPIRADO", "Expirado"

    class Entrega(models.TextChoices):
        DELIVERY_LIMA = "delivery_lima", "Delivery en Lima"
        RECOJO = "recojo", "Recojo"
        COURIER_PROVINCIA = "courier_provincia", "Courier a provincias"

    # El token (no el id) es lo que ve la clienta: evita enumerar pedidos ajenos (IDOR).
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    cliente = models.ForeignKey("accounts.Customer", on_delete=models.PROTECT, related_name="pedidos")
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE_PAGO, db_index=True)
    tipo_venta = models.CharField(max_length=12, choices=[("stock_local", "Stock en Lima"), ("por_encargo", "Por encargo")], default="stock_local")

    subtotal_pen = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    envio_pen = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    total_pen = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    adelanto_pen = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    saldo_pen = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    metodo_entrega = models.CharField(max_length=20, choices=Entrega.choices, default=Entrega.DELIVERY_LIMA)
    zona_envio = models.ForeignKey("shipping.ShippingZone", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    direccion_entrega = models.JSONField(default=dict, blank=True, help_text="Copia de la dirección al momento de comprar.")
    notas = models.TextField(blank=True)

    # Reservado para boleta/factura (sin implementar).
    doc_tipo = models.CharField(max_length=3, blank=True)
    doc_numero = models.CharField(max_length=15, blank=True)

    expira_en = models.DateTimeField(null=True, blank=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "pedido"
        indexes = [models.Index(fields=["estado", "expira_en"])]

    def __str__(self):
        return f"Pedido #{self.pk}"

    @property
    def monto_a_cobrar(self):
        """Lo que hay que pagar para pasar a PAGADO: adelanto en pre-order, total en stock local."""
        return self.adelanto_pen if self.tipo_venta == "por_encargo" and self.adelanto_pen else self.total_pen


class OrderItem(models.Model):
    pedido = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variante = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT, related_name="+")
    nombre_snapshot = models.CharField(max_length=240)
    sku_snapshot = models.CharField(max_length=40)
    precio_unitario = models.DecimalField("precio congelado (S/)", max_digits=9, decimal_places=2)
    cantidad = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(cantidad__gt=0), name="orderitem_cantidad_positiva")]

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


class OrderStatusHistory(models.Model):
    pedido = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(max_length=15, blank=True)
    estado_nuevo = models.CharField(max_length=15)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    nota = models.CharField(max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en", "id"]
        verbose_name = "cambio de estado"
        verbose_name_plural = "historial de estados"
