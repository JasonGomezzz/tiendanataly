import uuid

from django.db import models
from django.db.models import Q


class Cart(models.Model):
    """Carrito de una persona (con cuenta o invitada, identificada por token en cookie)."""

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.CASCADE, related_name="carts")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito {self.token}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variante = models.ForeignKey("catalog.ProductVariant", on_delete=models.CASCADE, related_name="+")
    cantidad = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "variante"], name="un_item_por_variante_en_carrito"),
            models.CheckConstraint(condition=Q(cantidad__gt=0), name="item_cantidad_positiva"),
        ]
