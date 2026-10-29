"""Permisos por rol (admin de Django) y aislamiento por propietaria en la API (sin IDOR)."""
import pytest
from django.conf import settings
from django.urls import reverse

from apps.accounts.models import Address
from apps.core.models import AuditLog
from apps.catalog.models import Product
from tests.factories import make_customer, make_order, make_product

pytestmark = pytest.mark.django_db


def admin_url(name, *args):
    return reverse(f"admin:{name}", args=args)


# --- Los roles no son superusuarios -----------------------------------------

def test_administradora_y_staff_no_son_superusuarios(admin_role, staff_role):
    assert not admin_role.is_superuser and not staff_role.is_superuser


def test_la_url_del_admin_usa_la_ruta_configurada():
    assert admin_url("index") == f"/{settings.ADMIN_URL_PATH}"


# --- Administradora ---------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "catalog_product_changelist",
        "orders_order_changelist",
        "payments_payment_changelist",
        "core_storesettings_changelist",
        "core_exchangerate_changelist",
        "core_auditlog_changelist",
        "inventory_inventorymovement_changelist",
        "shipping_shippingzone_changelist",
        "legal_complaint_changelist",
    ],
)
def test_administradora_accede_a_su_area(client, admin_role, name):
    client.force_login(admin_role)
    assert client.get(admin_url(name)).status_code == 200


@pytest.mark.parametrize("name", ["accounts_user_changelist", "auth_group_changelist", "otp_totp_totpdevice_changelist"])
def test_administradora_no_gestiona_usuarios_ni_grupos_ni_2fa(client, admin_role, name):
    client.force_login(admin_role)
    assert client.get(admin_url(name)).status_code == 403


def test_administradora_ve_costos_y_margenes(client, admin_role):
    product, _ = make_product()
    client.force_login(admin_role)
    html = client.get(admin_url("catalog_product_change", product.pk)).content.decode()
    assert "precio_compra_usd" in html and "margen" in html


# --- Staff ------------------------------------------------------------------

@pytest.mark.parametrize("name", ["catalog_product_changelist", "orders_order_changelist", "inventory_inventorymovement_changelist"])
def test_staff_accede_a_productos_y_pedidos(client, staff_role, name):
    client.force_login(staff_role)
    assert client.get(admin_url(name)).status_code == 200


@pytest.mark.parametrize(
    "name",
    [
        "payments_payment_changelist",
        "core_storesettings_changelist",
        "core_exchangerate_changelist",
        "core_auditlog_changelist",
        "accounts_user_changelist",
        "accounts_customer_changelist",
        "legal_complaint_changelist",
        "integrations_webhookoutbox_changelist",
    ],
)
def test_staff_no_ve_finanzas_ni_usuarios(client, staff_role, name):
    client.force_login(staff_role)
    assert client.get(admin_url(name)).status_code == 403


def test_staff_no_ve_costos_ni_margenes_en_el_producto(client, staff_role):
    product, _ = make_product()
    client.force_login(staff_role)
    html = client.get(admin_url("catalog_product_change", product.pk)).content.decode()
    assert "precio_compra_usd" not in html
    assert "margen" not in html.replace("margin", "")
    assert "precio_venta_pen" not in html


def test_staff_no_puede_enviar_precios_aunque_los_manipule(client, staff_role):
    product, _ = make_product()
    client.force_login(staff_role)
    r = client.post(admin_url("catalog_product_change", product.pk), {"precio_compra_usd": "1", "precio_venta_pen": "1", "margen": "1"})
    product.refresh_from_db()
    assert product.precio_venta_pen == 100 and r.status_code in (200, 302)


def test_staff_no_puede_eliminar_productos(client, staff_role):
    product, _ = make_product()
    client.force_login(staff_role)
    assert client.get(admin_url("catalog_product_delete", product.pk)).status_code == 403


# --- Clientas, anónimos y superusuario --------------------------------------

def test_una_clienta_no_entra_al_admin(client, customer_user):
    client.force_login(customer_user)
    r = client.get(admin_url("catalog_product_changelist"))
    assert r.status_code == 302 and "login" in r.url


def test_un_anonimo_no_entra_al_admin(client):
    r = client.get(admin_url("catalog_product_changelist"))
    assert r.status_code == 302 and "login" in r.url


def test_el_superusuario_tecnico_si_accede_a_usuarios(client, superuser):
    client.force_login(superuser)
    assert client.get(admin_url("accounts_user_changelist")).status_code == 200


# --- 2FA obligatorio en el admin --------------------------------------------

def test_con_2fa_activo_un_staff_sin_verificar_no_entra(client, admin_role, settings):
    settings.ADMIN_REQUIRE_2FA = True
    client.force_login(admin_role)
    r = client.get(admin_url("catalog_product_changelist"))
    assert r.status_code == 302 and "login" in r.url


# --- Auditoría ---------------------------------------------------------------

def test_los_cambios_en_el_admin_quedan_en_el_log_de_auditoria(client, staff_role):
    product, _ = make_product()
    client.force_login(staff_role)
    data = {
        "nombre": "Nombre nuevo", "slug": product.slug, "marca": product.marca_id, "categoria": product.categoria_id,
        "estado": "publicado", "tipo_venta": "stock_local", "orden": 0,
        "variantes-TOTAL_FORMS": 0, "variantes-INITIAL_FORMS": 0, "variantes-MIN_NUM_FORMS": 0, "variantes-MAX_NUM_FORMS": 1000,
        "imagenes-TOTAL_FORMS": 0, "imagenes-INITIAL_FORMS": 0, "imagenes-MIN_NUM_FORMS": 0, "imagenes-MAX_NUM_FORMS": 1000,
    }
    r = client.post(admin_url("catalog_product_change", product.pk), data)
    assert r.status_code == 302
    log = AuditLog.objects.get(modelo="catalog.Product")
    assert log.usuario == staff_role and log.accion == "editar" and "nombre" in log.cambios


# --- API: sin IDOR ----------------------------------------------------------

def test_endpoints_privados_requieren_sesion(api):
    for url in ("/api/v1/me/", "/api/v1/me/addresses/", "/api/v1/me/orders/"):
        assert api.get(url).status_code in (401, 403)


def test_una_clienta_no_ve_direcciones_de_otra(api, customer_user, other_customer_user):
    mine = Address.objects.create(customer=customer_user.customer, destinatario="Yo", telefono="1", distrito="Miraflores", direccion="Av. 1")
    api.force_authenticate(other_customer_user)
    assert api.get(f"/api/v1/me/addresses/{mine.pk}/").status_code == 404
    assert api.patch(f"/api/v1/me/addresses/{mine.pk}/", {"distrito": "X"}, format="json").status_code == 404
    assert api.delete(f"/api/v1/me/addresses/{mine.pk}/").status_code == 404
    assert api.get("/api/v1/me/addresses/").json() == []
    assert Address.objects.filter(pk=mine.pk).exists()


def test_una_clienta_no_puede_asignar_una_direccion_a_otra(api, customer_user, other_customer_user):
    api.force_authenticate(customer_user)
    r = api.post(
        "/api/v1/me/addresses/",
        {"destinatario": "Yo", "telefono": "1", "distrito": "Surco", "direccion": "Calle 2", "customer": other_customer_user.customer.pk},
        format="json",
    )
    assert r.status_code == 201
    assert Address.objects.get(pk=r.json()["id"]).customer == customer_user.customer


def test_una_clienta_no_ve_pedidos_de_otra(api, customer_user, other_customer_user):
    _, (v,) = make_product(stock_units=2)
    mine = make_order(v, customer=customer_user.customer)
    api.force_authenticate(other_customer_user)
    assert api.get("/api/v1/me/orders/").json()["results"] == []
    assert api.get(f"/api/v1/me/orders/{mine.public_token}/").status_code == 404
    api.force_authenticate(customer_user)
    assert api.get(f"/api/v1/me/orders/{mine.public_token}/").status_code == 200


def test_el_seguimiento_publico_usa_token_no_id_secuencial(api):
    _, (v,) = make_product(stock_units=2)
    order = make_order(v, customer=make_customer())
    assert api.get(f"/api/v1/orders/track/{order.public_token}/").status_code == 200
    assert api.get(f"/api/v1/orders/track/{order.pk}/").status_code == 404


# --- API: el catálogo no filtra datos internos -------------------------------

def test_el_catalogo_publico_no_expone_costos_ni_borradores(api):
    visible, _ = make_product(slug="visible")
    make_product(slug="oculto", estado=Product.Estado.BORRADOR)
    data = api.get("/api/v1/products/").json()
    assert [p["slug"] for p in data["results"]] == ["visible"]
    detail = api.get("/api/v1/products/visible/").json()
    for secret in ("precio_compra_usd", "margen", "notas_internas", "estado"):
        assert secret not in detail
    assert api.get("/api/v1/products/oculto/").status_code == 404


def test_producto_sin_precio_no_se_muestra(api):
    product, _ = make_product(slug="sin-precio")
    Product.objects.filter(pk=product.pk).update(precio_venta_pen=None)
    assert api.get("/api/v1/products/").json()["results"] == []
