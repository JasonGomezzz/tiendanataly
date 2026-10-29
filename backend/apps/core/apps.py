from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class TiendaAdminConfig(AdminConfig):
    """Reemplaza el AdminSite por defecto por uno con 2FA TOTP opcional."""

    default_site = "apps.core.admin_site.TiendaAdminSite"


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"
    verbose_name = "Configuración"
