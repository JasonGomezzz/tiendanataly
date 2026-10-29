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
    "bandolero-cuadrado": 2,  # 1 negro + 1 blanco
    "set-4-splash": 0,  # cantidad pendiente
    "splash-peach": 0,  # cantidad pendiente
    "panalero-rosado-juicy": 0,  # cantidad pendiente
    "reloj-bebe-plateado": 0,  # cantidad pendiente
    "set-reloj-aeropostale-rosado": 0,  # cantidad pendiente
    "set-guess-red": 0,  # cantidad pendiente
    "splash-midnight-marshmallow": 0,  # cantidad pendiente
    "splash-pina-tropicale": 0,  # cantidad pendiente
}


def png_bytes(fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "pink").save(buf, fmt)
    return buf.getvalue()


# --- Seed --------------------------------------------------------------------

PRECIOS_CONFIRMADOS = {
    "bolso-corazon-rojo": 120,
    "bolso-corazon-negro-brillos": 130,
    "bolso-corazon-plateado-monograma": 120,
    "panalero-rosado-juicy": 130,
    "reloj-bebe-plateado": 80,
    "set-reloj-aeropostale-rosado": 100,
    "mochila-negra-acolchada": 150,
    "bandolero-cuadrado": 130,
    "crema-corporal-cucumber": 40,
    "splash-clasica": 50,
    "set-guess-red": 180,
    "set-4-splash": 75,
    "set-mini-eau-de-parfum-bombshell": 90,
}


def test_seed_carga_los_precios_confirmados_y_publica_solo_lo_completo():
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    assert Product.objects.count() == 18
    for slug, price in PRECIOS_CONFIRMADOS.items():
        assert Product.objects.get(slug=slug).precio_venta_pen == price, slug
    # Sin costos cargados: la administradora los completa con la calculadora.
    assert not Product.objects.exclude(precio_compra_usd=None, margen=None).exists()
    publicados = set(Product.objects.filter(estado="publicado").values_list("slug", flat=True))
    assert publicados == {"bolso-corazon-rojo", "bolso-corazon-negro-brillos", "bolso-corazon-plateado-monograma", "mochila-negra-acolchada", "bandolero-cuadrado", "set-mini-eau-de-parfum-bombshell"}
    # Todo lo demás sigue en borrador hasta tener stock y precio.
    assert not Product.objects.exclude(slug__in=publicados).exclude(estado="borrador").exists()
    assert not Product.objects.filter(precio_venta_pen=None, estado="publicado").exists()


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
    assert Product.objects.count() == 18
    assert InventoryMovement.objects.count() == movements
    assert stock.audit_stock() == []


def test_seed_carga_las_fotos_disponibles_y_marca_las_que_faltan():
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    assert not Product.objects.get(slug="bolso-corazon-rojo").sin_imagen
    assert Product.objects.get(slug="bandolero-cuadrado").imagenes.count() == 2
    assert Product.objects.get(slug="splash-bare-vanilla").sin_imagen
    for slug in ("splash-clasica", "splash-midnight-marshmallow", "splash-pina-tropicale"):
        assert not Product.objects.get(slug=slug).sin_imagen, slug


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


def test_seed_carga_la_oferta_2_por_90_del_splash_clasica():
    call_command("seed_inventory", dir=str(SEED), verbosity=0)
    splash = Product.objects.get(slug="splash-clasica")
    assert (splash.oferta_cantidad, splash.oferta_precio) == (2, 90)
    assert not Product.objects.exclude(slug="splash-clasica").exclude(oferta_cantidad=None).exists()
