import io
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.catalog.models import Product, ProductImage
from apps.core.models import AuditLog, ExchangeRate, StoreSettings
from apps.inventory import services as stock
from apps.inventory.models import InventoryMovement
from apps.orders import services as orders
from apps.orders.models import Order
from apps.payments.models import Payment
from tests.factories import make_order, make_product

pytestmark = pytest.mark.django_db
A = "/api/v1/admin"


def png(name="foto.png"):
    buf = io.BytesIO()
    Image.new("RGB", (6, 6), "pink").save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@pytest.fixture
def as_admin(api, admin_role):
    api.force_authenticate(admin_role)
    return api


@pytest.fixture
def as_staff(api, staff_role):
    api.force_authenticate(staff_role)
    return api


@pytest.fixture
def catalog(db):
    from apps.catalog.models import Brand, Category

    Brand.objects.get_or_create(slug="vs", defaults={"nombre": "VS"})
    Category.objects.get_or_create(slug="bolsos", defaults={"nombre": "Bolsos"})
    return Brand.objects.get(slug="vs"), Category.objects.get(slug="bolsos")


# --- Acceso ------------------------------------------------------------------

@pytest.mark.parametrize("url", ["/me/", "/meta/", "/dashboard/", "/products/", "/orders/", "/store-settings/", "/audit-log/", "/exchange-rates/"])
def test_anonimas_y_clientas_no_entran_al_panel(api, customer_user, url):
    assert api.get(f"{A}{url}").status_code in (401, 403)
    api.force_authenticate(customer_user)
    assert api.get(f"{A}{url}").status_code == 403


def test_un_usuario_staff_sin_rol_no_entra(api, db):
    from tests.factories import make_user

    api.force_authenticate(make_user("suelto", staff=True))
    assert api.get(f"{A}/dashboard/").status_code == 403


def test_con_2fa_activo_una_sesion_sin_verificar_no_entra(as_admin, settings):
    settings.ADMIN_REQUIRE_2FA = True
    assert as_admin.get(f"{A}/dashboard/").status_code == 403


def test_me_informa_rol_y_permisos(as_admin):
    data = as_admin.get(f"{A}/me/").json()
    assert data["rol"] == "administradora" and data["permisos"]["catalog.ver_finanzas"] is True


def test_staff_tiene_menos_permisos(api, staff_role):
    api.force_authenticate(staff_role)
    data = api.get(f"{A}/me/").json()
    assert data["rol"] == "staff" and not data["permisos"]["catalog.ver_finanzas"] and not data["permisos"]["payments.change_payment"]


@pytest.mark.parametrize(
    "method,url",
    [("get", "/store-settings/"), ("get", "/audit-log/"), ("get", "/exchange-rates/"), ("post", "/exchange-rates/"), ("post", "/pricing/calculate/"), ("patch", "/store-settings/")],
)
def test_staff_no_accede_a_finanzas_ni_configuracion(as_staff, method, url):
    assert getattr(as_staff, method)(f"{A}{url}", {}, format="json").status_code == 403


def test_staff_no_puede_aprobar_pagos_ni_ve_comprobantes(as_staff):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    payment = Payment.objects.create(pedido=order, proveedor="manual_yape_plin", monto=100, idempotency_key="k", estado="en_revision")
    assert as_staff.post(f"{A}/payments/{payment.pk}/approve/").status_code == 403
    assert "pagos" not in as_staff.get(f"{A}/orders/{order.pk}/").json()


# --- Productos ---------------------------------------------------------------

def test_staff_no_ve_ni_puede_cambiar_costos_y_precios(as_staff):
    product, _ = make_product(slug="p1", precio=Decimal("150"))
    data = as_staff.get(f"{A}/products/{product.pk}/").json()
    assert not any(k in data for k in ("precio_compra_usd", "margen", "precio_venta_pen"))
    as_staff.patch(f"{A}/products/{product.pk}/", {"precio_venta_pen": "1", "nombre": "Nuevo nombre"}, format="json")
    product.refresh_from_db()
    assert product.precio_venta_pen == Decimal("150") and product.nombre == "Nuevo nombre"
    assert not any("precio" in k for k in as_staff.get(f"{A}/products/").json()[0])


def test_administradora_ve_y_edita_costos(as_admin):
    product, _ = make_product(slug="p2", precio=Decimal("150"))
    assert as_admin.get(f"{A}/products/{product.pk}/").json()["precio_compra_usd"] == "30.00"
    as_admin.patch(f"{A}/products/{product.pk}/", {"precio_venta_pen": "175"}, format="json")
    product.refresh_from_db()
    assert product.precio_venta_pen == Decimal("175")


def test_crear_producto_desde_el_celular_con_variantes_y_stock_inicial(as_admin, catalog):
    brand, cat = catalog
    r = as_admin.post(f"{A}/products/", {
        "nombre": "Bolso Rojo Corazón", "marca": brand.pk, "categoria": cat.pk, "precio_compra_usd": "30",
        "variantes": [{"nombre": "Rojo", "atributo": "color", "stock": 3}, {"nombre": "Negro", "atributo": "color", "stock": 0}],
    }, format="json")
    assert r.status_code == 201, r.json()
    data = r.json()
    assert data["slug"] == "bolso-rojo-corazon" and data["estado"] == "borrador" and data["stock_total"] == 3
    assert InventoryMovement.objects.filter(variante__producto_id=data["id"], tipo="entrada", motivo="Stock inicial").count() == 1
    assert AuditLog.objects.filter(modelo="catalog.Product", accion="crear").exists()
    again = as_admin.post(f"{A}/products/", {"nombre": "Bolso Rojo Corazón", "marca": brand.pk, "categoria": cat.pk}, format="json").json()
    assert again["slug"] == "bolso-rojo-corazon-2"


def test_no_se_publica_sin_precio_ni_foto(as_admin, catalog):
    brand, cat = catalog
    product = Product.objects.create(nombre="X", slug="x", marca=brand, categoria=cat)
    assert as_admin.post(f"{A}/products/{product.pk}/publish/").status_code == 400
    as_admin.patch(f"{A}/products/{product.pk}/", {"precio_venta_pen": "99"}, format="json")
    assert as_admin.post(f"{A}/products/{product.pk}/publish/").status_code == 400  # falta foto
    ProductImage.objects.create(producto=product, imagen="productos/x.jpg")
    assert as_admin.post(f"{A}/products/{product.pk}/publish/").json()["estado"] in ("publicado", "agotado")
    assert as_admin.post(f"{A}/products/{product.pk}/hide/").json()["estado"] == "borrador"


def test_subir_fotos_valida_el_tipo_real(as_admin, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    product, _ = make_product(slug="fotos")
    fake = SimpleUploadedFile("virus.jpg", b"MZ no soy imagen", content_type="image/jpeg")
    assert as_admin.post(f"{A}/products/{product.pk}/images/", {"imagen": fake}, format="multipart").status_code == 400
    r = as_admin.post(f"{A}/products/{product.pk}/images/", {"imagen": [png("a.png"), png("b.png")]}, format="multipart")
    assert r.status_code == 201 and len(r.json()) == 2
    image_id = r.json()[0]["id"]
    assert as_admin.delete(f"{A}/products/{product.pk}/images/?imagen={image_id}").status_code == 204


def test_ajuste_de_stock_exige_motivo_y_respeta_lo_reservado(as_admin):
    _, (v,) = make_product(stock_units=2)
    url = f"{A}/variants/{v.pk}/adjust-stock/"
    assert as_admin.post(url, {"tipo": "ajuste", "cantidad": -1, "motivo": ""}, format="json").status_code == 400
    assert as_admin.post(url, {"tipo": "entrada", "cantidad": 3, "motivo": "Llegó pedido"}, format="json").json()["stock_disponible"] == 5
    stock.reserve(v, 5)
    assert as_admin.post(url, {"tipo": "ajuste", "cantidad": -1, "motivo": "Se dañó"}, format="json").status_code == 400
    assert stock.audit_stock() == []


def test_crear_variante_y_desactivarla(as_staff):
    product, _ = make_product(slug="vars")
    r = as_staff.post(f"{A}/products/{product.pk}/variants/", {"nombre": "Azul", "atributo": "color"}, format="json")
    assert r.status_code == 201
    assert as_staff.patch(f"{A}/variants/{r.json()['id']}/", {"activo": False}, format="json").json()["activo"] is False


# --- Calculadora ---------------------------------------------------------------

def test_calculadora_usa_tipo_de_cambio_y_configuracion(as_admin):
    assert as_admin.post(f"{A}/pricing/calculate/", {"precio_usd": "30"}, format="json").status_code == 400  # sin tipo de cambio
    ExchangeRate.objects.create(usd_pen=Decimal("3.80"))
    cfg = StoreSettings.load()
    cfg.envio_estimado_usd, cfg.margen_default, cfg.redondeo_multiplo = Decimal("5"), Decimal("40"), 5
    cfg.save()
    r = as_admin.post(f"{A}/pricing/calculate/", {"precio_usd": "30"}, format="json").json()
    assert r["precio_final"] == "175.00" and r["costo_pen"] == "133.00"
    r2 = as_admin.post(f"{A}/pricing/calculate/", {"precio_usd": "30", "margen": "60", "comision_pct": "4"}, format="json").json()
    assert Decimal(r2["precio_final"]) > Decimal("195") and Decimal(r2["comision_pen"]) > 0


def test_tipo_de_cambio_se_registra_con_auditoria(as_admin):
    assert as_admin.post(f"{A}/exchange-rates/", {"usd_pen": "abc"}, format="json").status_code == 400
    assert as_admin.post(f"{A}/exchange-rates/", {"usd_pen": "3.75"}, format="json").status_code == 201
    assert as_admin.get(f"{A}/exchange-rates/").json()[0]["usd_pen"] == "3.7500"
    assert AuditLog.objects.filter(modelo="core.ExchangeRate").exists()


def test_ajustes_de_tienda_solo_administradora(as_admin):
    r = as_admin.patch(f"{A}/store-settings/", {"whatsapp": "51999000111", "minutos_reserva": 20}, format="json")
    assert r.status_code == 200 and StoreSettings.load().minutos_reserva == 20


# --- Pedidos y pagos -------------------------------------------------------------

def test_tablero_de_pedidos_filtra_por_estado_y_busca(as_admin):
    _, (v,) = make_product(stock_units=3)
    a, b = make_order(v), make_order(v)
    orders.transition(b, Order.Estado.PAGADO)
    assert {o["id"] for o in as_admin.get(f"{A}/orders/").json()} == {a.pk, b.pk}
    assert [o["id"] for o in as_admin.get(f"{A}/orders/?estado=PAGADO").json()] == [b.pk]
    assert [o["id"] for o in as_admin.get(f"{A}/orders/?q={a.pk}").json()] == [a.pk]


def test_transiciones_validas_e_invalidas_desde_el_panel(as_staff):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    assert as_staff.post(f"{A}/orders/{order.pk}/transition/", {"estado": "ENTREGADO"}, format="json").status_code == 409
    assert as_staff.post(f"{A}/orders/{order.pk}/transition/", {"estado": "inventado"}, format="json").status_code == 400
    r = as_staff.post(f"{A}/orders/{order.pk}/transition/", {"estado": "PAGADO", "nota": "Pago en tienda"}, format="json")
    assert r.status_code == 200 and r.json()["estado"] == "PAGADO" and "EN_LIMA" in r.json()["siguientes"]
    assert r.json()["historial"][-1]["usuario"] == "empleada@example.com"


def test_aprobar_y_rechazar_pagos_desde_el_panel(as_admin):
    _, (v,) = make_product(stock_units=2)
    order = make_order(v)
    p1 = Payment.objects.create(pedido=order, proveedor="manual_yape_plin", monto=order.total_pen, idempotency_key="k1", estado="en_revision")
    bad = Payment.objects.create(pedido=order, proveedor="manual_yape_plin", monto=order.total_pen, idempotency_key="k2", estado="en_revision")
    assert as_admin.post(f"{A}/payments/{bad.pk}/reject/", {"nota": "Monto incorrecto"}, format="json").status_code == 200
    detail = as_admin.post(f"{A}/payments/{p1.pk}/approve/").json()
    assert detail["estado"] == "PAGADO" and {p["estado"] for p in detail["pagos"]} == {"aprobado", "rechazado"}
    assert as_admin.post(f"{A}/payments/{p1.pk}/approve/").status_code == 409  # ya procesado


def test_dashboard_de_la_administradora_y_del_staff(as_admin, api, staff_role):
    _, (v,) = make_product(stock_units=1)
    order = make_order(v)
    payment = Payment.objects.create(pedido=order, proveedor="manual_yape_plin", monto=order.total_pen, idempotency_key="kk", estado="en_revision")
    data = as_admin.get(f"{A}/dashboard/").json()
    assert data["pedidos_hoy"] == 1 and data["pagos_en_revision"] == 1 and data["stock_bajo"][0]["libre"] == 0
    assert data["ventas_hoy"] == "0" and len(data["ventas_semana"]) == 7
    as_admin.post(f"{A}/payments/{payment.pk}/approve/")
    assert Decimal(as_admin.get(f"{A}/dashboard/").json()["ventas_hoy"]) == order.total_pen
    api.force_authenticate(staff_role)
    staff_data = api.get(f"{A}/dashboard/").json()
    assert "ventas_hoy" not in staff_data and "pagos_en_revision" not in staff_data and staff_data["pedidos_hoy"] == 1


def test_el_log_de_auditoria_se_consulta_desde_el_panel(as_admin):
    product, _ = make_product(slug="aud")
    as_admin.patch(f"{A}/products/{product.pk}/", {"nombre": "Cambiado"}, format="json")
    rows = as_admin.get(f"{A}/audit-log/").json()
    assert rows[0]["accion"] == "editar" and rows[0]["usuario"] == "tia@example.com"


def test_meta_para_los_formularios(as_staff):
    make_product(slug="m")
    meta = as_staff.get(f"{A}/meta/").json()
    assert meta["marcas"] and meta["transiciones"]["PENDIENTE_PAGO"]
