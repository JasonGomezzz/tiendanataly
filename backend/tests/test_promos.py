from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.catalog.models import Product
from apps.core.models import StoreSettings
from apps.pricing.promos import cart_discount, pair_discount, validate_offer
from apps.shipping.models import ShippingZone
from tests.factories import make_product

pytestmark = pytest.mark.django_db

CHECKOUT = {
    "nombre": "Ana", "telefono": "987654321", "metodo_entrega": "delivery_lima",
    "direccion": {"departamento": "Lima", "provincia": "Lima", "distrito": "Miraflores", "direccion": "Av. 1"},
    "acepta_privacidad": True, "acepta_terminos": True,
}


def splash(stock=(3, 3)):
    """Splash de S/ 50 con oferta 2 por S/ 90 y dos fragancias."""
    product, variants = make_product(slug="splash", precio=Decimal("50"), variants=[("Love Spell", stock[0]), ("Bare Vanilla", stock[1])])
    Product.objects.filter(pk=product.pk).update(oferta_cantidad=2, oferta_precio=Decimal("90"))
    product.refresh_from_db()
    return product, variants


def add(api, variant, qty=1):
    return api.post("/api/v1/cart/items/", {"variante_id": variant.pk, "cantidad": qty}, format="json")


# --- Cálculo puro --------------------------------------------------------------

@pytest.mark.parametrize(
    "qty,expected",
    [(1, "0"), (2, "10"), (3, "10"), (4, "20"), (5, "20"), (6, "30")],
)
def test_dos_por_90_con_precio_unitario_50(qty, expected):
    assert pair_discount(Decimal("50"), qty, 2, Decimal("90")) == Decimal(expected)


def test_sin_oferta_o_con_oferta_que_no_conviene_no_descuenta():
    assert pair_discount(Decimal("50"), 4, None, None) == 0
    assert pair_discount(Decimal("50"), 4, 2, Decimal("120")) == 0  # más caro que comprarlas sueltas


def test_oferta_para_tres_unidades():
    assert pair_discount(Decimal("40"), 7, 3, Decimal("100")) == Decimal("40")  # 2 grupos × (120 − 100)


@pytest.mark.parametrize(
    "price,qty,offer,error",
    [
        (50, None, None, False),
        (50, 2, 90, False),
        (50, 2, None, True),
        (50, None, 90, True),
        (50, 1, 40, True),
        (50, 2, 100, True),
        (50, 2, 120, True),
    ],
)
def test_validacion_de_la_oferta(price, qty, offer, error):
    assert bool(validate_offer(Decimal(price), qty, None if offer is None else Decimal(offer))) is error


def test_el_modelo_rechaza_una_oferta_invalida():
    product, _ = make_product(slug="x", precio=Decimal("50"))
    product.oferta_cantidad, product.oferta_precio = 2, Decimal("100")
    with pytest.raises(ValidationError):
        product.full_clean(exclude=["marca", "categoria", "slug"])


def test_descuento_agrupa_variantes_del_mismo_producto_pero_no_de_productos_distintos():
    product, _ = splash()
    other, _ = make_product(slug="otro", precio=Decimal("50"))
    total, by_product = cart_discount([(product, 1, Decimal("50")), (product, 1, Decimal("50")), (other, 2, Decimal("50"))])
    assert total == Decimal("10") and set(by_product) == {product.pk}


# --- Carrito y checkout ----------------------------------------------------------

def test_el_carrito_muestra_el_descuento_y_el_total(api):
    _, (a, b) = splash()
    add(api, a)
    cart = api.get("/api/v1/cart/").json()
    assert cart["descuento"] == "0.00" and cart["total"] == "50.00"
    add(api, b)  # otra fragancia del mismo splash: ya son 2
    cart = api.get("/api/v1/cart/").json()
    assert (cart["subtotal"], cart["descuento"], cart["total"]) == ("100.00", "10.00", "90.00")
    assert cart["items"][0]["oferta"] == {"cantidad": 2, "precio": "90.00"}


def test_el_producto_publico_expone_la_oferta(api):
    splash()
    data = api.get("/api/v1/products/splash/").json()
    assert data["oferta_cantidad"] == 2 and data["oferta_precio"] == "90.00"


def test_checkout_aplica_la_oferta_y_el_pago_es_el_total_con_descuento(api):
    _, (a, b) = splash()
    zona = ShippingZone.objects.create(nombre="Delivery", metodo="delivery_lima", costo=Decimal("10"))
    add(api, a, 2)
    add(api, b, 1)  # 3 unidades: 1 par (90) + 1 suelta (50)
    data = api.post("/api/v1/checkout/", {**CHECKOUT, "zona_id": zona.pk}, format="json").json()
    assert (data["subtotal_pen"], data["descuento_pen"], data["envio_pen"], data["total_pen"]) == ("150.00", "10.00", "10.00", "150.00")
    assert data["monto_a_cobrar"] == "150.00"
    assert "Oferta aplicada" in data["whatsapp"]["text"]


def test_el_precio_de_la_oferta_se_congela_aunque_cambie_despues(api):
    product, (a, b) = splash()
    zona = ShippingZone.objects.create(nombre="Delivery", metodo="delivery_lima", costo=Decimal("0"))
    add(api, a)
    add(api, b)
    token = api.post("/api/v1/checkout/", {**CHECKOUT, "zona_id": zona.pk}, format="json").json()["token"]
    Product.objects.filter(pk=product.pk).update(oferta_cantidad=None, oferta_precio=None)
    assert api.get(f"/api/v1/orders/track/{token}/").json()["total_pen"] == "90.00"


def test_pedido_por_encargo_calcula_el_adelanto_sobre_el_total_con_descuento(api):
    cfg = StoreSettings.load()
    cfg.pct_adelanto = Decimal("50")
    cfg.save()
    product, (a, b) = splash()
    Product.objects.filter(pk=product.pk).update(tipo_venta="por_encargo")
    zona = ShippingZone.objects.create(nombre="Delivery", metodo="delivery_lima", costo=Decimal("0"))
    add(api, a)
    add(api, b)
    data = api.post("/api/v1/checkout/", {**CHECKOUT, "zona_id": zona.pk}, format="json").json()
    assert data["total_pen"] == "90.00" and data["adelanto_pen"] == "45.00"


# --- Panel -------------------------------------------------------------------------

def test_el_panel_valida_y_oculta_la_oferta_al_staff(api, admin_role, staff_role):
    product, _ = make_product(slug="panel", precio=Decimal("50"))
    api.force_authenticate(admin_role)
    bad = api.patch(f"/api/v1/admin/products/{product.pk}/", {"oferta_cantidad": 2, "oferta_precio": "100"}, format="json")
    assert bad.status_code == 400
    ok = api.patch(f"/api/v1/admin/products/{product.pk}/", {"oferta_cantidad": 2, "oferta_precio": "90"}, format="json")
    assert ok.status_code == 200 and ok.json()["oferta_precio"] == "90.00"
    api.force_authenticate(staff_role)
    data = api.get(f"/api/v1/admin/products/{product.pk}/").json()
    assert "oferta_cantidad" not in data
    api.patch(f"/api/v1/admin/products/{product.pk}/", {"oferta_precio": "1"}, format="json")
    product.refresh_from_db()
    assert product.oferta_precio == Decimal("90.00")  # el staff no puede cambiar precios
