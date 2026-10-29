"""Servicio de stock: única vía para cambiar stock_disponible / stock_reservado.

Todas las operaciones bloquean la fila de la variante con select_for_update dentro
de una transacción, y dejan un InventoryMovement. Dos compradoras por la última
unidad nunca pueden ganar las dos.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant

from .models import InventoryMovement, StockReservation


class StockError(Exception):
    pass


class InsufficientStock(StockError):
    pass


def _lock_variant(variant_id):
    return ProductVariant.objects.select_for_update().select_related("producto").get(pk=variant_id)


def _record(variant, tipo, d_disp, d_res, motivo="", user=None, order=None, reservation=None):
    return InventoryMovement.objects.create(
        variante=variant,
        tipo=tipo,
        delta_disponible=d_disp,
        delta_reservado=d_res,
        disponible_resultante=variant.stock_disponible,
        reservado_resultante=variant.stock_reservado,
        motivo=motivo,
        usuario=user,
        pedido=order,
        reserva=reservation,
    )


def _sync_product_state(variant):
    Product.objects.get(pk=variant.producto_id).sync_agotado()


def _check_qty(qty):
    if not isinstance(qty, int) or qty <= 0:
        raise StockError("La cantidad debe ser un entero mayor que cero.")


@transaction.atomic
def add_stock(variant, qty, motivo, user=None):
    """Ingreso de mercadería."""
    _check_qty(qty)
    v = _lock_variant(variant.pk)
    v.stock_disponible += qty
    v.save(update_fields=["stock_disponible"])
    _record(v, InventoryMovement.Tipo.ENTRADA, qty, 0, motivo, user)
    _sync_product_state(v)
    return v


@transaction.atomic
def adjust_stock(variant, delta, motivo, user=None):
    """Corrección manual (suma o resta). Exige motivo y no deja el físico por debajo de lo reservado."""
    if not motivo or not motivo.strip():
        raise StockError("El motivo es obligatorio.")
    if not isinstance(delta, int) or delta == 0:
        raise StockError("El ajuste debe ser un entero distinto de cero.")
    v = _lock_variant(variant.pk)
    nuevo = v.stock_disponible + delta
    if nuevo < v.stock_reservado:
        raise StockError(f"No se puede dejar el stock físico en {nuevo}: hay {v.stock_reservado} reservadas.")
    v.stock_disponible = nuevo
    v.save(update_fields=["stock_disponible"])
    _record(v, InventoryMovement.Tipo.AJUSTE, delta, 0, motivo, user)
    _sync_product_state(v)
    return v


def reserve_many(items, order=None, minutes=None):
    """Reserva atómica de varias variantes: o se reserva todo o nada.

    `items` es una lista de (variant, qty). Se bloquea en orden de id para evitar deadlocks.
    """
    if minutes is None:
        from apps.core.models import StoreSettings

        minutes = StoreSettings.load().minutos_reserva
    merged = {}
    for variant, qty in items:
        _check_qty(qty)
        merged[variant.pk] = merged.get(variant.pk, 0) + qty

    with transaction.atomic():
        reservations = []
        expira = timezone.now() + timedelta(minutes=minutes)
        for variant_id in sorted(merged):
            qty = merged[variant_id]
            v = _lock_variant(variant_id)
            if not v.activo:
                raise StockError(f"«{v}» no está disponible.")
            if v.disponible < qty:
                raise InsufficientStock(f"Stock insuficiente para «{v}»: quedan {v.disponible}.")
            v.stock_reservado += qty
            v.save(update_fields=["stock_reservado"])
            reservation = StockReservation.objects.create(variante=v, pedido=order, cantidad=qty, expira_en=expira)
            _record(v, InventoryMovement.Tipo.RESERVA, 0, qty, "Reserva por checkout", None, order, reservation)
            reservations.append(reservation)
        return reservations


def reserve(variant, qty, order=None, minutes=None):
    return reserve_many([(variant, qty)], order=order, minutes=minutes)[0]


def _lock_active_reservation(reservation_id):
    reservation = StockReservation.objects.select_for_update().get(pk=reservation_id)
    return reservation if reservation.estado == StockReservation.Estado.ACTIVA else None


@transaction.atomic
def release(reservation, motivo="Reserva liberada"):
    """Libera una reserva activa (pago no realizado, cancelación o expiración). Devuelve True si liberó."""
    locked = _lock_active_reservation(reservation.pk)
    if locked is None:
        return False
    v = _lock_variant(locked.variante_id)
    v.stock_reservado -= locked.cantidad
    v.save(update_fields=["stock_reservado"])
    locked.estado = StockReservation.Estado.LIBERADA
    locked.save(update_fields=["estado"])
    _record(v, InventoryMovement.Tipo.LIBERACION, 0, -locked.cantidad, motivo, None, locked.pedido, locked)
    _sync_product_state(v)
    return True


@transaction.atomic
def consume(reservation, motivo="Venta confirmada"):
    """Convierte una reserva activa en venta: baja el stock físico y la reserva."""
    locked = _lock_active_reservation(reservation.pk)
    if locked is None:
        raise StockError("La reserva ya no está activa.")
    v = _lock_variant(locked.variante_id)
    v.stock_disponible -= locked.cantidad
    v.stock_reservado -= locked.cantidad
    v.save(update_fields=["stock_disponible", "stock_reservado"])
    locked.estado = StockReservation.Estado.CONSUMIDA
    locked.save(update_fields=["estado"])
    _record(v, InventoryMovement.Tipo.VENTA, -locked.cantidad, -locked.cantidad, motivo, None, locked.pedido, locked)
    _sync_product_state(v)
    return v


def release_expired(now=None):
    """Libera reservas vencidas sin pedido asociado. (Las de pedidos las maneja orders.services.)"""
    now = now or timezone.now()
    qs = StockReservation.objects.filter(estado=StockReservation.Estado.ACTIVA, expira_en__lte=now, pedido__isnull=True)
    return sum(1 for r in qs if release(r, "Reserva vencida"))


def audit_stock():
    """Compara los contadores con el libro de movimientos. Devuelve la lista de discrepancias."""
    from django.db.models import Sum

    problems = []
    for v in ProductVariant.objects.all():
        sums = InventoryMovement.objects.filter(variante=v).aggregate(d=Sum("delta_disponible"), r=Sum("delta_reservado"))
        disp, res = sums["d"] or 0, sums["r"] or 0
        activas = (
            StockReservation.objects.filter(variante=v, estado=StockReservation.Estado.ACTIVA).aggregate(t=Sum("cantidad"))["t"] or 0
        )
        if disp != v.stock_disponible or res != v.stock_reservado or activas != v.stock_reservado:
            problems.append(
                f"{v.sku}: contadores {v.stock_disponible}/{v.stock_reservado}, movimientos {disp}/{res}, reservas activas {activas}"
            )
    return problems
