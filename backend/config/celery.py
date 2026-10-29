import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("tiendanataly")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "liberar-reservas-vencidas": {
        "task": "apps.orders.tasks.expire_pending_orders",
        "schedule": 60.0,
    },
    "enviar-eventos-pendientes": {
        "task": "apps.integrations.tasks.flush_outbox",
        "schedule": 30.0,
    },
}
