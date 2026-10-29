from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    name = "apps.integrations"
    label = "integrations"
    verbose_name = "Integraciones"

    def ready(self):
        from . import signals  # noqa: F401
