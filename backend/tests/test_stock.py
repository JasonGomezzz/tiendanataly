import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant
from apps.inventory import services as stock
from apps.inventory.models import InventoryMovement, StockReservation
from tests.factories import make_product

pytestmark = pytest.mark.django_db


def test_reservar_baja_lo_disponible_sin_tocar_el_fisico():
    _, (v,) = make_product(stock_units=3)
    stock.reserve(v, 2)
    v.refresh_from_db()
    assert (v.stock_disponible, v.stock_reservado, v.disponible) == (3, 2, 1)


def test_no_se_puede_reservar_mas_de_lo_disponible():
    _, (v,) = make_product(stock_units=1)
    stock.reserve(v, 1)
    with pytest.raises(stock.InsufficientStock):
        stock.reserve(v, 1)


def test_reserva_multiple_es_todo_o_nada():
    _, (a,) = make_product(stock_units=2)
    _, (b,) = make_product(stock_units=1)
    with pytest.raises(stock.InsufficientStock):
        stock.reserve_many([(a, 1), (b, 2)])
    a.refresh_from_db()
    assert a.stock_reservado == 0
    assert StockReservation.objects.count() == 0


def test_liberar_devuelve_la_unidad_y_es_idempotente():
    _, (v,) = make_product(stock_units=1)
    r = stock.reserve(v, 1)
    assert stock.release(r) is True
    assert stock.release(r) is False
    v.refresh_from_db()
    assert (v.stock_disponible, v.stock_reservado) == (1, 0)


def test_consumir_baja_fisico_y_reservado():
    _, (v,) = make_product(stock_units=2)
    r = stock.reserve(v, 1)
    stock.consume(r)
    v.refresh_from_db()
    assert (v.stock_disponible, v.stock_reservado) == (1, 0)
    with pytest.raises(stock.StockError):
        stock.consume(r)


def test_ajuste_exige_motivo_y_no_baja_de_lo_reservado():
    _, (v,) = make_product(stock_units=2)
    stock.reserve(v, 2)
    with pytest.raises(stock.StockError, match="motivo"):
        stock.adjust_stock(v, -1, "  ")
    with pytest.raises(stock.StockError, match="reservadas"):
        stock.adjust_stock(v, -1, "Se dañó")


def test_cada_cambio_deja_un_movimiento_y_el_stock_audita_limpio():
    _, (v,) = make_product(stock_units=5)
    r1 = stock.reserve(v, 2)
    stock.consume(r1)
    r2 = stock.reserve(v, 1)
    stock.release(r2)
    stock.adjust_stock(v, -1, "Conteo físico")
    tipos = list(InventoryMovement.objects.filter(variante=v).order_by("id").values_list("tipo", flat=True))
    assert tipos == ["entrada", "reserva", "venta", "reserva", "liberacion", "ajuste"]
    assert stock.audit_stock() == []


def test_audit_detecta_manipulacion_directa_del_contador():
    _, (v,) = make_product(stock_units=2)
    ProductVariant.objects.filter(pk=v.pk).update(stock_disponible=5)
    assert len(stock.audit_stock()) == 1


def test_reservas_vencidas_sin_pedido_se_liberan():
    _, (v,) = make_product(stock_units=1)
    r = stock.reserve(v, 1, minutes=15)
    StockReservation.objects.filter(pk=r.pk).update(expira_en=timezone.now() - timedelta(minutes=1))
    assert stock.release_expired() == 1
    v.refresh_from_db()
    assert v.stock_reservado == 0


def test_el_producto_pasa_a_agotado_y_vuelve_a_publicado():
    product, (v,) = make_product(stock_units=1)
    r = stock.reserve(v, 1)
    stock.consume(r)
    product.refresh_from_db()
    assert product.estado == Product.Estado.AGOTADO
    stock.add_stock(v, 1, "Reposición")
    product.refresh_from_db()
    assert product.estado == Product.Estado.PUBLICADO


def test_un_borrador_no_se_publica_solo_al_entrar_stock():
    product, (v,) = make_product(stock_units=0, estado=Product.Estado.BORRADOR)
    stock.add_stock(v, 3, "Ingreso")
    product.refresh_from_db()
    assert product.estado == Product.Estado.BORRADOR


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != "postgresql", reason="select_for_update requiere PostgreSQL")
def test_concurrencia_dos_compradoras_por_la_ultima_unidad_solo_una_gana():
    _, (v,) = make_product(stock_units=1)
    buyers = 8
    barrier = threading.Barrier(buyers)
    results = []

    def buy():
        try:
            barrier.wait()
            stock.reserve(v, 1)
            results.append("ok")
        except stock.InsufficientStock:
            results.append("sin_stock")
        finally:
            connection.close()

    threads = [threading.Thread(target=buy) for _ in range(buyers)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    v.refresh_from_db()
    assert results.count("ok") == 1
    assert results.count("sin_stock") == buyers - 1
    assert (v.stock_disponible, v.stock_reservado) == (1, 1)
    assert StockReservation.objects.filter(variante=v, estado="activa").count() == 1
    assert stock.audit_stock() == []
