"""Ofertas por cantidad: «llevando N por S/ X».

Regla: se agrupan las unidades del MISMO producto (sumando todas sus variantes, p. ej. dos fragancias
distintas del mismo splash) y cada grupo completo de N unidades cuesta el precio de oferta. Las unidades
que sobran se cobran al precio normal. Nunca encarece: si la oferta no conviene, no se aplica.
"""
from decimal import Decimal

CENT = Decimal("0.01")


def pair_discount(unit_price, qty, offer_qty, offer_price):
    """Descuento (S/) que corresponde a `qty` unidades con la oferta del producto."""
    if not offer_qty or offer_qty < 2 or offer_price is None or qty < offer_qty:
        return Decimal("0")
    groups = qty // offer_qty
    normal = Decimal(unit_price) * offer_qty * groups
    discount = normal - Decimal(offer_price) * groups
    return max(discount, Decimal("0")).quantize(CENT)


def cart_discount(lines):
    """`lines`: iterable de (producto, cantidad, precio_unitario). Devuelve el descuento total y por producto."""
    per_product = {}
    for product, qty, price in lines:
        entry = per_product.setdefault(product.pk, [product, 0, price])
        entry[1] += qty
    by_product = {}
    for product, qty, price in per_product.values():
        d = pair_discount(price, qty, product.oferta_cantidad, product.oferta_precio)
        if d > 0:
            by_product[product.pk] = d
    return sum(by_product.values(), Decimal("0")), by_product


def validate_offer(unit_price, offer_qty, offer_price):
    """Mensaje de error o None. La oferta debe ser una rebaja real y venir completa."""
    if not offer_qty and offer_price is None:
        return None
    if not offer_qty or offer_price is None:
        return "La oferta necesita la cantidad y el precio por esa cantidad."
    if offer_qty < 2:
        return "La oferta es por 2 o más unidades."
    if unit_price and Decimal(offer_price) >= Decimal(unit_price) * offer_qty:
        return "El precio de oferta debe ser menor que comprar las unidades por separado."
    return None
