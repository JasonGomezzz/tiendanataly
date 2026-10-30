from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.models import StoreSettings
from apps.payments.models import BankAccount

STORE_FIELDS = {
    "nombre_tienda", "whatsapp", "yape_numero", "yape_titular", "plin_numero", "plin_titular",
    "razon_social", "ruc", "direccion_fiscal",
}


class Command(BaseCommand):
    help = (
        "Carga datos reales del negocio (WhatsApp, Yape/Plin y cuentas bancarias) desde un YAML que NO se sube a git. "
        "Ver seed/negocio.example.yaml. También se pueden editar desde /admin → Ajustes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Por defecto: seed/negocio.local.yaml")

    def handle(self, *args, **options):
        candidates = [Path(options["file"])] if options["file"] else [settings.SEED_DIR / "negocio.local.yaml", settings.BASE_DIR.parent / "seed" / "negocio.local.yaml"]
        path = next((c for c in candidates if c.exists()), None)
        if path is None:
            raise CommandError("No encontré negocio.local.yaml. Copia seed/negocio.example.yaml y complétalo.")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        cfg = StoreSettings.load()
        unknown = set(data.get("tienda", {})) - STORE_FIELDS
        if unknown:
            raise CommandError(f"Campos desconocidos en «tienda»: {', '.join(sorted(unknown))}")
        for key, value in data.get("tienda", {}).items():
            setattr(cfg, key, str(value))
        cfg.save()

        created = 0
        for i, acc in enumerate(data.get("cuentas", []), start=1):
            _, is_new = BankAccount.objects.update_or_create(
                banco=acc["banco"], numero=str(acc["numero"]),
                defaults={
                    "etiqueta": acc.get("etiqueta", ""), "cci": str(acc.get("cci", "")),
                    "titular": acc.get("titular", ""), "activa": acc.get("activa", True), "orden": acc.get("orden", i),
                },
            )
            created += is_new
        self.stdout.write(self.style.SUCCESS(f"Datos del negocio cargados: {len(data.get('tienda', {}))} ajustes, {created} cuenta(s) nueva(s)."))
