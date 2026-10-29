from celery import shared_task

from . import services


@shared_task
def expire_pending_orders():
    return services.expire_pending_orders()
