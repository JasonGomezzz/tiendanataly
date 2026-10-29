from pathlib import Path

import yaml
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import Brand, Category, Product, ProductImage, ProductVariant
from apps.core.models import StoreSettings
from apps.inventory import services as stock
from apps.shipping.models import ShippingZone

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


class Command(BaseCommand):
    help = "Carga el inventario inicial desde seed/inventory.yaml (idempotente, productos en borrador, sin precios)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", help="Carpeta del seed (por defecto /seed o ./seed del repo)")

    def _seed_dir(self, option):
        candidates = [Path(option)] if option else [settings.SEED_DIR, settings.BASE_DIR.parent / "seed"]
        for path in candidates:
            if (path / "inventory.yaml").exists():
                return path
        raise CommandError("No encontré inventory.yaml. Usa --dir con la carpeta del seed.")

    @staticmethod
    def _images_for(folder, slug):
        """<slug>.jpg es la principal; <slug>-2.jpg, <slug>-3.jpg… son las siguientes."""
        found = []
        for ext in IMAGE_EXTENSIONS:
            found += sorted(folder.glob(f"{slug}{ext}")) + sorted(folder.glob(f"{slug}-[0-9]{ext}"))
        return sorted(found, key=lambda path: (path.stem != slug, path.name))

    @transaction.atomic
    def handle(self, *args, **options):
        seed_dir = self._seed_dir(options["dir"])
        data = yaml.safe_load((seed_dir / "inventory.yaml").read_text(encoding="utf-8"))
        StoreSettings.load()

        # Zonas de envío PLACEHOLDER (costos por confirmar); solo se crean si no hay ninguna.
        if not ShippingZone.objects.exists():
            for zone in data.get("zonas_envio", []):
                ShippingZone.objects.create(**zone)

        for c in data["categorias"]:
            Category.objects.update_or_create(slug=c["slug"], defaults={"nombre": c["nombre"], "orden": c.get("orden", 0)})
        for b in data["marcas"]:
            Brand.objects.update_or_create(slug=b["slug"], defaults={"nombre": b["nombre"]})

        created = without_image = 0
        for p in data["productos"]:
            product, is_new = Product.objects.get_or_create(
                slug=p["slug"],
                defaults={
                    "nombre": p["nombre"],
                    "marca": Brand.objects.get(slug=p["marca"]),
                    "categoria": Category.objects.get(slug=p["categoria"]),
                    "linea": p.get("linea", ""),
                    "descripcion": p.get("descripcion", ""),
                    "notas_internas": p.get("notas_internas", ""),
                    "orden": p.get("orden", 0),
                    "estado": Product.Estado.BORRADOR,
                    "tipo_venta": p.get("tipo_venta", Product.TipoVenta.STOCK_LOCAL),
                },
            )
            created += is_new
            for v in p["variantes"]:
                variant, v_new = ProductVariant.objects.get_or_create(
                    sku=v["sku"],
                    defaults={"producto": product, "nombre": v["nombre"], "atributo": v.get("atributo", "unico")},
                )
                if v_new and v.get("stock", 0) > 0:
                    stock.add_stock(variant, v["stock"], "Stock inicial (seed)")

            if not product.imagenes.exists():
                paths = self._images_for(seed_dir / "images", p["slug"])
                if not paths:
                    without_image += 1
                    self.stdout.write(self.style.WARNING(f"  sin imagen: {product.slug}"))
                for order, image_path in enumerate(paths):
                    with image_path.open("rb") as fh:
                        img = ProductImage(producto=product, alt=product.nombre, orden=order)
                        img.imagen.save(image_path.name, File(fh), save=True)

        self.stdout.write(self.style.SUCCESS(f"Seed listo: {created} producto(s) nuevo(s), {without_image} sin imagen. Todos en borrador y sin precios."))
