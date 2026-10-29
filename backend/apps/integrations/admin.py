from django.contrib import admin

from .models import WebhookOutbox


@admin.register(WebhookOutbox)
class WebhookOutboxAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "evento", "estado", "intentos")
    list_filter = ("estado", "evento")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
