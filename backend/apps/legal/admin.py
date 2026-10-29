from django.contrib import admin
from django.utils import timezone

from apps.core.admin_mixins import AuditedAdminMixin

from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("correlativo", "creado_en", "nombre", "tipo", "estado")
    list_filter = ("estado", "tipo")
    search_fields = ("correlativo", "nombre", "doc_numero", "pedido_ref")
    readonly_fields = [f.name for f in Complaint._meta.fields if f.name not in ("estado", "respuesta", "respondido_en")]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if obj.respuesta and obj.estado == Complaint.Estado.ATENDIDO and not obj.respondido_en:
            obj.respondido_en = timezone.now()
        super().save_model(request, obj, form, change)
