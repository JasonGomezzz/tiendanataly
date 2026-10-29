import io
import urllib.request
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.catalog.models import Collection, Product
from apps.core.models import StoreSettings
from apps.integrations import tasks as integration_tasks
from apps.orders.models import Order
from apps.payments.models import Payment
from tests.factories import make_order, make_product

pytestmark = pytest.mark.django_db


def png():
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "pink").save(buf, "PNG")
    return SimpleUploadedFile("captura.png", buf.getvalue(), content_type="image/png")


# --- Catálogo ----------------------------------------------------------------

def test_filtros_por_categoria_marca_precio_y_disponibilidad(api):
    make_product(slug="barato", stock_units=3, precio=Decimal("50"))
    make_product(slug="caro", stock_units=3, precio=Decimal("500"))
    make_product(slug="agotado", stock_units=0, precio=Decimal("80"))
    slugs = lambda qs: sorted(p["slug"] for p in api.get(f"/api/v1/products/?{qs}").json()["results"])
    assert slugs("") == ["agotado", "barato", "caro"]
    assert slugs("precio_max=100") == ["agotado", "barato"]
    assert slugs("disponible=true") == ["barato", "caro"]
    assert slugs("disponible=false") == ["agotado"]
    assert slugs("categoria=bolsos&marca=vs") == ["agotado", "barato", "caro"]
    assert slugs("categoria=no-existe") == []


def test_ultimas_unidades_y_agotado_en_el_listado(api):
    make_product(slug="ultima", stock_units=1)
    make_product(slug="mucho", stock_units=9)
    make_product(slug="nada", stock_units=0)
    by_slug = {p["slug"]: p for p in api.get("/api/v1/products/").json()["results"]}
    assert by_slug["ultima"]["ultimas_unidades"] and not by_slug["ultima"]["agotado"]
    assert not by_slug["mucho"]["ultimas_unidades"]
    assert by_slug["nada"]["agotado"]
    assert [p["slug"] for p in api.get("/api/v1/products/?ultimas=true").json()["results"]] == ["ultima"]


def test_la_disponibilidad_descuenta_lo_reservado(api):
    _, (v,) = make_product(slug="reservada", stock_units=2)
    make_order(v, 2)
    detail = api.get("/api/v1/products/reservada/").json()
    assert detail["variantes"][0]["disponible"] == 0 and detail["variantes"][0]["agotado"] and detail["agotado"]


def test_busqueda_por_texto(api):
    make_product(slug="bolso-corazon-rojo")
    make_product(slug="mochila-negra")
    assert [p["slug"] for p in api.get("/api/v1/products/?search=corazon").json()["results"]] == ["bolso-corazon-rojo"]


def test_productos_relacionados_excluyen_el_actual(api):
    make_product(slug="a")
    make_product(slug="b")
    assert [p["slug"] for p in api.get("/api/v1/products/a/related/").json()] == ["b"]


def test_colecciones_filtran_productos(api):
    p, _ = make_product(slug="regalo")
    make_product(slug="otro")
    c = Collection.objects.create(nombre="Navidad", slug="navidad")
    c.productos.add(p)
    assert [x["slug"] for x in api.get("/api/v1/products/?coleccion=navidad").json()["results"]] == ["regalo"]
    assert api.get("/api/v1/collections/").json()[0]["slug"] == "navidad"


def test_resenas_se_moderan_antes_de_publicarse(api, customer_user):
    make_product(slug="rese")
    api.force_authenticate(customer_user)
    assert api.post("/api/v1/products/rese/reviews/", {"autor": "Ana", "puntaje": 5, "comentario": "Linda"}, format="json").status_code == 201
    assert api.get("/api/v1/products/rese/reviews/").json() == []
    from apps.catalog.models import Review

    Review.objects.update(estado="aprobada")
    assert len(api.get("/api/v1/products/rese/reviews/").json()) == 1
    assert api.get("/api/v1/products/rese/").json()["puntaje_promedio"] == 5.0


def test_avisame_cuando_vuelva(api):
    _, (v,) = make_product(stock_units=0)
    assert api.post(f"/api/v1/variants/{v.pk}/stock-alerts/", {}, format="json").status_code == 400
    assert api.post(f"/api/v1/variants/{v.pk}/stock-alerts/", {"email": "a@b.com"}, format="json").status_code == 201


def test_libro_de_reclamaciones_genera_correlativo(api):
    data = {
        "nombre": "Ana", "doc_tipo": "DNI", "doc_numero": "12345678", "domicilio": "Calle 1", "telefono": "999", "email": "a@b.com",
        "descripcion_bien": "Bolso", "tipo": "reclamo", "detalle": "Llegó con falla", "pedido_consumidor": "Cambio",
    }
    r = api.post("/api/v1/complaints/", data, format="json")
    assert r.status_code == 201 and r.json()["correlativo"].endswith("-000001")
    assert api.post("/api/v1/complaints/", {**data, "es_menor": True}, format="json").status_code == 400  # falta apoderado


# --- Pago manual Yape/Plin ---------------------------------------------------

def test_subir_comprobante_deja_el_pago_en_revision_con_monto_del_servidor(api):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v, precio=Decimal("180"))
    r = api.post(f"/api/v1/orders/{order.public_token}/payments/manual/", {"comprobante": png(), "metodo": "yape", "monto": "1"}, format="multipart")
    assert r.status_code == 201 and r.json() == {"estado": "en_revision", "monto": "180.00"}
    assert Payment.objects.get().comprobante.name.startswith("comprobantes/")


def test_el_comprobante_debe_ser_una_imagen_real(api):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    fake = SimpleUploadedFile("captura.png", b"no soy una imagen", content_type="image/png")
    assert api.post(f"/api/v1/orders/{order.public_token}/payments/manual/", {"comprobante": fake, "metodo": "yape"}, format="multipart").status_code == 400
    assert Payment.objects.count() == 0


def test_no_se_sube_comprobante_a_un_pedido_ya_pagado(api):
    from apps.orders import services

    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    services.transition(order, Order.Estado.PAGADO)
    assert api.post(f"/api/v1/orders/{order.public_token}/payments/manual/", {"comprobante": png(), "metodo": "plin"}, format="multipart").status_code == 409


def test_el_seguimiento_publico_muestra_el_estado_del_pago(api):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    api.post(f"/api/v1/orders/{order.public_token}/payments/manual/", {"comprobante": png(), "metodo": "plin"}, format="multipart")
    data = api.get(f"/api/v1/orders/track/{order.public_token}/").json()
    assert data["pagos"][0]["estado"] == "en_revision"
    assert "comprobante" not in data["pagos"][0]


def test_datos_publicos_de_la_tienda_incluyen_yape_y_plin(api):
    cfg = StoreSettings.load()
    cfg.yape_numero = "999888777"
    cfg.save()
    assert api.get("/api/v1/store-settings/public/").json()["yape_numero"] == "999888777"


# --- Revalidación del frontend ------------------------------------------------

def test_guardar_un_producto_pide_revalidar_el_frontend(settings, monkeypatch):
    settings.REVALIDATE_SECRET = "secreto-de-prueba"
    settings.FRONTEND_URL = "http://frontend:3000"
    calls = []

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: calls.append(req) or Resp())
    assert integration_tasks.revalidate_frontend() is True
    req = calls[0]
    assert req.full_url == "http://frontend:3000/api/revalidate" and req.get_header("X-revalidate-secret") == "secreto-de-prueba"


def test_sin_secreto_no_se_intenta_revalidar(settings):
    settings.REVALIDATE_SECRET = ""
    assert integration_tasks.revalidate_frontend() is False
