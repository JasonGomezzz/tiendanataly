"""Calculadora de precio. Funciones puras con Decimal, sin acceso a la base de datos."""
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
HUNDRED = Decimal("100")


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class PriceBreakdown:
    costo_usd: Decimal          # precio + envío + impuestos, en US$
    costo_pen: Decimal          # costo convertido a soles
    margen_pen: Decimal
    comision_pen: Decimal       # lo que se llevará la pasarela sobre el precio final
    precio_sin_redondeo: Decimal
    precio_final: Decimal       # redondeado a múltiplo comercial
    ganancia_neta: Decimal      # precio_final - comisión - costo_pen


def _d(value, name):
    try:
        d = Decimal(str(value))
    except Exception:
        raise PricingError(f"{name} inválido")
    if d < 0:
        raise PricingError(f"{name} no puede ser negativo")
    return d


def round_commercial(amount, multiple=5):
    """Sube al siguiente múltiplo (p. ej. S/ 5). Con múltiplo <= 1 redondea a céntimos."""
    amount = Decimal(amount)
    multiple = Decimal(multiple)
    if multiple <= 1:
        return amount.quantize(CENT, rounding=ROUND_HALF_UP)
    return ((amount / multiple).to_integral_value(rounding=ROUND_CEILING) * multiple).quantize(CENT)


def calculate_price(
    *,
    precio_usd,
    tipo_cambio,
    envio_usd=0,
    impuestos_pct=0,
    margen_pen=0,
    comision_pct=0,
    igv_rate="0.18",
    multiplo=5,
):
    """(precio_usd + envío + impuestos) × tipo de cambio + margen, con la comisión de pasarela
    incorporada (gross-up) y redondeo comercial hacia arriba.

    La comisión se cobra sobre el precio final y lleva IGV, por eso se divide por
    (1 − comisión × (1 + IGV)) en vez de sumarla, para que la ganancia no se erosione.
    """
    precio_usd = _d(precio_usd, "precio_usd")
    tipo_cambio = _d(tipo_cambio, "tipo_cambio")
    envio_usd = _d(envio_usd, "envio_usd")
    impuestos_pct = _d(impuestos_pct, "impuestos_pct")
    margen_pen = Decimal(str(margen_pen))
    comision_pct = _d(comision_pct, "comision_pct")
    igv = _d(igv_rate, "igv_rate")
    if tipo_cambio == 0:
        raise PricingError("El tipo de cambio debe ser mayor que cero")

    costo_usd = precio_usd + envio_usd + precio_usd * impuestos_pct / HUNDRED
    costo_pen = costo_usd * tipo_cambio
    neto = costo_pen + margen_pen

    tasa = comision_pct / HUNDRED * (1 + igv)
    factor = 1 - tasa
    if factor <= 0:
        raise PricingError("La comisión es demasiado alta")
    bruto = neto / factor
    final = round_commercial(bruto, multiplo)
    comision = (final * tasa).quantize(CENT, rounding=ROUND_HALF_UP)

    return PriceBreakdown(
        costo_usd=costo_usd.quantize(CENT, rounding=ROUND_HALF_UP),
        costo_pen=costo_pen.quantize(CENT, rounding=ROUND_HALF_UP),
        margen_pen=margen_pen.quantize(CENT, rounding=ROUND_HALF_UP),
        comision_pen=comision,
        precio_sin_redondeo=bruto.quantize(CENT, rounding=ROUND_HALF_UP),
        precio_final=final,
        ganancia_neta=(final - comision - costo_pen).quantize(CENT, rounding=ROUND_HALF_UP),
    )


def calculate_for_product(product, *, margen_pen=None):
    """Aplica la configuración vigente de la tienda (tipo de cambio, envío, comisión) a un producto."""
    from apps.core.models import ExchangeRate, StoreSettings
    from django.conf import settings

    rate = ExchangeRate.current()
    if rate is None:
        raise PricingError("No hay un tipo de cambio configurado")
    if product.precio_compra_usd is None:
        raise PricingError("El producto no tiene precio de compra")
    cfg = StoreSettings.load()
    return calculate_price(
        precio_usd=product.precio_compra_usd,
        tipo_cambio=rate.usd_pen,
        envio_usd=cfg.envio_estimado_usd,
        impuestos_pct=cfg.impuestos_estimados_pct,
        margen_pen=cfg.margen_default if margen_pen is None else margen_pen,
        comision_pct=cfg.pct_comision,
        igv_rate=settings.IGV_RATE,
        multiplo=cfg.redondeo_multiplo,
    )
