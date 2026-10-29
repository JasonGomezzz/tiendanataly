from django.contrib import admin, messages

from apps.catalog.admin import thumbnail
from apps.core.admin_mixins import AuditedAdminMixin
from apps.core.audit import log_action
from apps.core.models import AuditLog

from . import services
from .models import Payment, PaymentEvent


@admin.register(Payment)
class PaymentAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "creado_en", "pedido", "proveedor", "metodo", "monto", "estado", "ver_comprobante")
    list_filter = ("estado", "proveedor", "metodo")
    search_fields = ("pedido__id", "external_id", "idempotency_key")
    actions = ["aprobar", "rechazar"]
    readonly_fields = [f.name for f in Payment._meta.fields if f.name not in ("nota", "comprobante")] + ["ver_comprobante"]
    exclude = ("comprobante",)

    @admin.display(description="comprobante")
    def ver_comprobante(self, obj):
        return thumbnail(obj.comprobante, 80) if obj.comprobante else "—"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Aprobar pagos seleccionados", permissions=["change"])
    def aprobar(self, request, queryset):
        for payment in queryset:
            try:
                services.approve_payment(payment, user=request.user)
            except services.PaymentError as exc:
                self.message_user(request, f"Pago {payment.pk}: {exc}", messages.ERROR)
                continue
            log_action(request, AuditLog.Accion.ACCION, payment, cambios={"accion": "aprobar_pago"})
            self.message_user(request, f"Pago {payment.pk} aprobado.", messages.SUCCESS)

    @admin.action(description="Rechazar pagos seleccionados", permissions=["change"])
    def rechazar(self, request, queryset):
        for payment in queryset:
            try:
                services.reject_payment(payment, user=request.user, nota="Rechazado desde el admin")
            except services.PaymentError as exc:
                self.message_user(request, f"Pago {payment.pk}: {exc}", messages.ERROR)
                continue
            log_action(request, AuditLog.Accion.ACCION, payment, cambios={"accion": "rechazar_pago"})


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("recibido_en", "proveedor", "tipo", "event_id", "procesado")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
