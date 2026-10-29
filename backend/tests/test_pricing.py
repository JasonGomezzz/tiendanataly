from decimal import Decimal

import pytest

from apps.core.models import ExchangeRate, StoreSettings
from apps.catalog.models import Product
from apps.pricing.services import PricingError, calculate_for_product, calculate_price, round_commercial


def test_formula_base_sin_comision():
    # (30 + 5 + 0) × 3.80 + 40 = 173 → sube a múltiplo de 5 = 175
    r = calculate_price(precio_usd=30, envio_usd=5, tipo_cambio="3.80", margen_pen=40, multiplo=5)
    assert r.costo_usd == Decimal("35.00")
    assert r.costo_pen == Decimal("133.00")
    assert r.precio_sin_redondeo == Decimal("173.00")
    assert r.precio_final == Decimal("175.00")
    assert r.comision_pen == Decimal("0.00")
    assert r.ganancia_neta == Decimal("42.00")


def test_impuestos_se_calculan_sobre_el_precio_en_usd():
    r = calculate_price(precio_usd=100, impuestos_pct=10, tipo_cambio=4, multiplo=1)
    assert r.costo_usd == Decimal("110.00")
    assert r.precio_final == Decimal("440.00")


def test_comision_se_incorpora_sin_erosionar_la_ganancia():
    r = calculate_price(precio_usd=30, envio_usd=5, tipo_cambio="3.80", margen_pen=40, comision_pct="3.5", multiplo=5)
    # La ganancia neta (después de comisión + IGV) no baja del margen pedido por el redondeo.
    assert r.precio_final > Decimal("173")
    assert r.ganancia_neta >= Decimal("40.00") - Decimal("0.01")
    assert r.comision_pen > 0


def test_el_redondeo_siempre_sube():
    assert round_commercial(Decimal("173.01"), 5) == Decimal("175.00")
    assert round_commercial(Decimal("175.00"), 5) == Decimal("175.00")
    assert round_commercial(Decimal("173.126"), 1) == Decimal("173.13")


def test_la_precision_es_decimal_no_flotante():
    r = calculate_price(precio_usd="0.10", tipo_cambio="3", multiplo=1)
    assert r.precio_final == Decimal("0.30")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"precio_usd": -1, "tipo_cambio": 3.8},
        {"precio_usd": 10, "tipo_cambio": 0},
        {"precio_usd": 10, "tipo_cambio": 3.8, "comision_pct": 90},
        {"precio_usd": "abc", "tipo_cambio": 3.8},
    ],
)
def test_entradas_invalidas(kwargs):
    with pytest.raises(PricingError):
        calculate_price(**kwargs)


@pytest.mark.django_db
def test_calcular_para_producto_usa_la_configuracion_de_la_tienda():
    cfg = StoreSettings.load()
    cfg.envio_estimado_usd = Decimal("5")
    cfg.margen_default = Decimal("40")
    cfg.redondeo_multiplo = 5
    cfg.save()
    ExchangeRate.objects.create(usd_pen=Decimal("3.80"))
    product = Product(precio_compra_usd=Decimal("30"))
    assert calculate_for_product(product).precio_final == Decimal("175.00")


@pytest.mark.django_db
def test_sin_tipo_de_cambio_falla_con_mensaje_claro():
    with pytest.raises(PricingError, match="tipo de cambio"):
        calculate_for_product(Product(precio_compra_usd=Decimal("30")))
