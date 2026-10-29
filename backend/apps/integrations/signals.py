"""Cuando el catálogo cambia, avisa al frontend para regenerar sus páginas (ISR on-demand)."""
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from apps.catalog.models import Collection, Product, ProductImage, ProductVariant

from .tasks import schedule_revalidation

STOCK_ONLY = {"stock_disponible", "stock_reservado"}


@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=ProductImage)
@receiver([post_save, post_delete], sender=Collection)
@receiver(m2m_changed, sender=Collection.productos.through)
def catalog_changed(sender, **kwargs):
    transaction.on_commit(schedule_revalidation)


@receiver([post_save, post_delete], sender=ProductVariant)
def variant_changed(sender, update_fields=None, **kwargs):
    # El stock cambia con cada reserva; la disponibilidad se refresca en el navegador, no hace falta regenerar.
    if update_fields and set(update_fields) <= STOCK_ONLY:
        return
    transaction.on_commit(schedule_revalidation)
