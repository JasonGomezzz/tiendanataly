import threading
from decimal import Decimal

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.catalog.models import Product
from apps.core.models import StoreSettings
from apps.inventory import services as stock
from apps.orders.models import Order
from apps.shipping.models import ShippingZone
from tests.factories import make_product

pytestmark = pytest.mark.django_db

CHECKOUT = {
    "nombre": "Ana Pérez", "telefono": "987654321", "metodo_entrega": "delivery_lima",
    "direccion": {"departamento": "Lima", "provincia": "Lima", "distrito": "Miraflores", "direccion": "Av. Larco 123"},
    "acepta_privacidad": True, "acepta_terminos": True,
}


@pytest.fixture
def zona(db):
    return ShippingZone.objects.create(nombre="Delivery Lima", metodo="delivery_lima", costo=Decimal("10"))


def add(api, variant, qty=1):
    return api.post("/api/v1/cart/items/", {"variante_id": variant.pk, "cantidad": qty}, format="json")


def pay(zona, **extra):
    return {**CHECKOUT, "zona_id": zona.pk, **extra}


# --- Carrito -----------------------------------------------------------------

def test_invitada_agrega_al_carrito_y_la_cookie_conserva_el_carrito(api):
    _, (v,) = make_product(stock_units=3, precio=Decimal("120"))
    r = add(api, v, 2)
    assert r.status_code == 201 and r.cookies["cart_token"]["httponly"]
    cart = api.get("/api/v1/cart/").json()
    assert cart["count"] == 2 and Decimal(cart["subtotal"]) == Decimal("240")
    assert APIClient().get("/api/v1/cart/").json()["count"] == 0  # otra persona no lo ve


def test_no_se_puede_agregar_mas_de_lo_disponible(api):
    _, (v,) = make_product(stock_units=1)
    assert add(api, v, 2).status_code == 400
    assert add(api, v, 1).status_code == 201
    assert add(api, v, 1).status_code == 400  # sumaría 2


def test_no_se_agregan_borradores_ni_productos_sin_precio(api):
    _, (draft,) = make_product(estado=Product.Estado.BORRADOR)
    assert add(api, draft).status_code == 400


def test_un_item_ajeno_no_se_puede_tocar(api):
    _, (v,) = make_product(stock_units=3)
    add(api, v)
    item_id = api.get("/api/v1/cart/").json()["items"][0]["id"]
    other = APIClient()
    assert other.patch(f"/api/v1/cart/items/{item_id}/", {"cantidad": 2}, format="json").status_code == 404
    assert other.delete(f"/api/v1/cart/items/{item_id}/").status_code == 404
    assert api.patch(f"/api/v1/cart/items/{item_id}/", {"cantidad": 2}, format="json").status_code == 200


def test_el_carrito_de_invitada_se_fusiona_al_iniciar_sesion(api, customer_user):
    _, (v,) = make_product(stock_units=3)
    add(api, v, 1)
    api.force_authenticate(customer_user)
    r = api.post("/api/v1/cart/merge/")
    assert r.status_code == 200 and r.json()["count"] == 1


# --- Checkout ----------------------------------------------------------------

def test_checkout_crea_pedido_reserva_stock_y_calcula_en_el_servidor(api, zona):
    _, (v,) = make_product(stock_units=2, precio=Decimal("150"))
    add(api, v, 2)
    r = api.post("/api/v1/checkout/", {**pay(zona), "total_pen": "1", "precio": "1"}, format="json")  # montos del cliente se ignoran
    assert r.status_code == 201, r.json()
    data = r.json()
    assert (data["subtotal_pen"], data["envio_pen"], data["total_pen"]) == ("300.00", "10.00", "310.00")
    assert data["estado"] == "PENDIENTE_PAGO"
    v.refresh_from_db()
    assert (v.stock_disponible, v.stock_reservado) == (2, 2)
    assert api.get("/api/v1/cart/").json()["count"] == 0
    assert stock.audit_stock() == []


def test_el_precio_se_congela_en_el_pedido(api, zona):
    product, (v,) = make_product(stock_units=1, precio=Decimal("100"))
    add(api, v)
    token = api.post("/api/v1/checkout/", pay(zona), format="json").json()["token"]
    Product.objects.filter(pk=product.pk).update(precio_venta_pen=Decimal("999"))
    assert api.get(f"/api/v1/orders/track/{token}/").json()["items"][0]["precio_unitario"] == "100.00"


def test_checkout_exige_consentimiento(api, zona):
    _, (v,) = make_product(stock_units=1)
    add(api, v)
    assert api.post("/api/v1/checkout/", pay(zona, acepta_privacidad=False), format="json").status_code == 400
    assert Order.objects.count() == 0


def test_checkout_con_bolsa_vacia_falla(api, zona):
    assert api.post("/api/v1/checkout/", pay(zona), format="json").status_code == 400


def test_checkout_valida_zona_y_direccion(api, zona):
    _, (v,) = make_product(stock_units=1)
    add(api, v)
    assert api.post("/api/v1/checkout/", {**pay(zona), "zona_id": 9999}, format="json").status_code == 400
    sin_dir = {k: val for k, val in pay(zona).items() if k != "direccion"}
    assert api.post("/api/v1/checkout/", sin_dir, format="json").status_code == 400
    recojo = ShippingZone.objects.create(nombre="Recojo", metodo="recojo", costo=0)
    ok = api.post("/api/v1/checkout/", {**sin_dir, "metodo_entrega": "recojo", "zona_id": recojo.pk}, format="json")
    assert ok.status_code == 201 and ok.json()["envio_pen"] == "0.00"


def test_si_otra_clienta_se_llevo_la_unidad_el_checkout_falla_sin_dejar_basura(api, zona):
    _, (v,) = make_product(stock_units=1)
    add(api, v)
    stock.reserve(v, 1)  # otra compradora ganó
    r = api.post("/api/v1/checkout/", pay(zona), format="json")
    assert r.status_code == 409 and r.json()["code"] == "sin_stock"
    assert Order.objects.count() == 0
    assert api.get("/api/v1/cart/").json()["count"] == 1  # su bolsa sigue ahí


def test_pedido_por_encargo_cobra_adelanto_y_no_reserva_stock(api, zona):
    cfg = StoreSettings.load()
    cfg.pct_adelanto = Decimal("40")
    cfg.save()
    product, (v,) = make_product(stock_units=0, precio=Decimal("200"))
    Product.objects.filter(pk=product.pk).update(tipo_venta="por_encargo")
    add(api, v)
    data = api.post("/api/v1/checkout/", pay(zona), format="json").json()
    assert data["tipo_venta"] == "por_encargo" and data["adelanto_pen"] == "84.00" and data["saldo_pen"] == "126.00"
    assert data["monto_a_cobrar"] == "84.00"
    v.refresh_from_db()
    assert v.stock_reservado == 0


def test_no_se_mezclan_stock_local_y_por_encargo(api, zona):
    _, (a,) = make_product(stock_units=2)
    p2, (b,) = make_product(stock_units=2)
    Product.objects.filter(pk=p2.pk).update(tipo_venta="por_encargo")
    add(api, a)
    add(api, b)
    assert api.post("/api/v1/checkout/", pay(zona), format="json").status_code == 400


def test_checkout_autenticada_usa_su_cuenta(api, zona, customer_user):
    _, (v,) = make_product(stock_units=1)
    api.force_authenticate(customer_user)
    add(api, v)
    assert api.post("/api/v1/checkout/", pay(zona), format="json").status_code == 201
    assert Order.objects.get().cliente.user == customer_user
    assert api.get("/api/v1/me/orders/").json()["count"] == 1


def test_mensaje_de_whatsapp_incluye_el_detalle(api, zona):
    cfg = StoreSettings.load()
    cfg.whatsapp = "51999111222"
    cfg.save()
    _, (v,) = make_product(slug="bolso-x", stock_units=1, precio=Decimal("150"))
    add(api, v)
    token = api.post("/api/v1/checkout/", pay(zona), format="json").json()["token"]
    wa = api.get(f"/api/v1/orders/{token}/whatsapp-message/").json()
    assert wa["url"].startswith("https://wa.me/51999111222?text=") and "Bolso X" in wa["text"] and "160.00" in wa["text"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != "postgresql", reason="requiere PostgreSQL")
def test_concurrencia_en_checkout_solo_una_compradora_se_lleva_la_ultima_unidad():
    zona = ShippingZone.objects.create(nombre="Delivery Lima", metodo="delivery_lima", costo=0)
    _, (v,) = make_product(stock_units=1)
    clients = [APIClient() for _ in range(6)]
    for c in clients:
        assert add(c, v).status_code == 201  # todas la tienen en su bolsa
    barrier = threading.Barrier(len(clients))
    codes = []

    def buy(client):
        try:
            barrier.wait()
            codes.append(client.post("/api/v1/checkout/", pay(zona), format="json").status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=buy, args=(c,)) for c in clients]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(codes) == [201] + [409] * (len(clients) - 1)
    assert Order.objects.count() == 1
    assert stock.audit_stock() == []
