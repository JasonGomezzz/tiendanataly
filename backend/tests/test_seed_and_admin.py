import io
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from PIL import Image

from apps.catalog.models import Product, ProductVariant
from apps.core.models import AuditLog
from apps.core.validators import validate_image_file
from apps.inventory.models import InventoryMovement
from apps.inventory import services as stock
from tests.factories import make_product

pytestmark = pytest.mark.django_db

SEED = Path(settings.BASE_DIR).parent / "seed"

EXPECTED_STOCK = {
    "bolso-corazon-rojo": 4,
    "bolso-corazon-negro-brillos": 2,
    "bolso-corazon-plateado-monograma": 2,
    "mochila-negra-acolchada": 1,
    "mochila-pink-deportiva": 1,
    "set-mini-eau-de-parfum-bombshell": 1,
    "splash-clasica": 0,  # 5 unidades pendientes de repartir por fragancia
    "splash-bare-vanilla": 2,
    "crema-corporal-cucumber": 2,
}


def png_bytes(fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "pink").save(buf, fmt)
    return buf.getvalue()


# --- Seed --------------------------------------------------------------------

def test_seed_carga_los_nueve_productos_en_borrador_sin_precios():
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    assert Product.objects.count() == 9
    assert set(Product.objects.values_list("estado", flat=True)) == {"borrador"}
    assert not Product.objects.exclude(precio_compra_usd=None, precio_venta_pen=None, margen=None).exists()


def test_seed_respeta_el_stock_inicial_de_la_tabla():
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    for slug, expected in EXPECTED_STOCK.items():
        product = Product.objects.get(slug=slug)
        assert sum(v.stock_disponible for v in product.variantes.all()) == expected, slug


def test_seed_de_splash_clasica_tiene_una_variante_por_fragancia():
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    names = set(ProductVariant.objects.filter(producto__slug="splash-clasica").values_list("nombre", flat=True))
    assert names == {"Pure Seduction", "Bare Vanilla", "Love Spell", "Velvet Petals"}


def test_seed_es_idempotente_y_el_stock_audita_limpio():
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    movements = InventoryMovement.objects.count()
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    assert Product.objects.count() == 9
    assert InventoryMovement.objects.count() == movements
    assert stock.audit_stock() == []


def test_seed_marca_productos_sin_imagen():
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    assert all(p.sin_imagen for p in Product.objects.all())


def test_la_crema_no_se_llama_curcuma_ni_queda_con_marca_inventada():
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    crema = Product.objects.get(slug="crema-corporal-cucumber")
    assert "cúrcuma" not in crema.nombre.lower() and crema.marca.slug == "por-confirmar"
    assert "PENDIENTE" in crema.notas_internas


# --- Subida de imágenes ------------------------------------------------------

def test_imagen_real_pasa_la_validacion():
    validate_image_file(SimpleUploadedFile("foto.png", png_bytes("PNG")))
    validate_image_file(SimpleUploadedFile("foto.jpg", png_bytes("JPEG")))


def test_un_ejecutable_renombrado_a_jpg_se_rechaza():
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        validate_image_file(SimpleUploadedFile("virus.jpg", b"MZ\x90\x00 esto no es una imagen"))


def test_formato_no_permitido_se_rechaza():
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="Formato"):
        validate_image_file(SimpleUploadedFile("anim.gif", png_bytes("GIF")))


def test_imagen_demasiado_grande_se_rechaza(settings):
    from django.core.exceptions import ValidationError

    settings.MAX_IMAGE_UPLOAD_BYTES = 10
    with pytest.raises(ValidationError, match="supera"):
        validate_image_file(SimpleUploadedFile("foto.png", png_bytes("PNG")))


def test_el_archivo_subido_se_renombra_con_uuid(settings, tmp_path):
    from apps.catalog.models import ProductImage

    settings.MEDIA_ROOT = tmp_path
    product, _ = make_product()
    img = ProductImage(producto=product)
    img.imagen.save("../../etc/mi foto.PNG", SimpleUploadedFile("x.png", png_bytes("PNG")))
    assert img.imagen.name.startswith("productos/") and ".." not in img.imagen.name and "mi foto" not in img.imagen.name


# --- Acciones del admin ------------------------------------------------------

def test_publicar_exige_precio_de_venta(client, admin_role):
    product, _ = make_product(estado=Product.Estado.BORRADOR, precio=None)
    client.force_login(admin_role)
    client.post(reverse("admin:catalog_product_changelist"), {"action": "publicar", "_selected_action": [product.pk]})
    product.refresh_from_db()
    assert product.estado == Product.Estado.BORRADOR
    Product.objects.filter(pk=product.pk).update(precio_venta_pen=120)
    client.post(reverse("admin:catalog_product_changelist"), {"action": "publicar", "_selected_action": [product.pk]})
    product.refresh_from_db()
    assert product.estado == Product.Estado.PUBLICADO
    assert AuditLog.objects.filter(accion="accion", objeto_id=str(product.pk)).exists()


def test_ajuste_manual_de_stock_con_motivo(client, admin_role):
    _, (v,) = make_product(stock_units=1)
    client.force_login(admin_role)
    url = reverse("admin:catalog_productvariant_changelist")
    client.post(url, {"action": "ajustar_stock", "_selected_action": [v.pk], "apply": "1", "tipo": "entrada", "cantidad": 3, "motivo": "Llegó pedido"})
    v.refresh_from_db()
    assert v.stock_disponible == 4
    mov = InventoryMovement.objects.filter(variante=v).first()
    assert mov.tipo == "entrada" and mov.motivo == "Llegó pedido" and mov.usuario == admin_role


def test_ajuste_sin_motivo_no_se_aplica(client, admin_role):
    _, (v,) = make_product(stock_units=1)
    client.force_login(admin_role)
    client.post(reverse("admin:catalog_productvariant_changelist"), {"action": "ajustar_stock", "_selected_action": [v.pk], "apply": "1", "tipo": "ajuste", "cantidad": -1, "motivo": ""})
    v.refresh_from_db()
    assert v.stock_disponible == 1


def test_el_stock_no_es_editable_a_mano_en_el_admin(client, admin_role):
    _, (v,) = make_product(stock_units=1)
    client.force_login(admin_role)
    html = client.get(reverse("admin:catalog_productvariant_change", args=[v.pk])).content.decode()
    assert 'name="stock_disponible"' not in html
