from django.contrib import admin

from apps.core.admin_mixins import AuditedAdminMixin

from .models import ShippingZone


@admin.register(ShippingZone)
class ShippingZoneAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "metodo", "costo", "courier", "activa", "orden")
    list_filter = ("metodo", "activa")
