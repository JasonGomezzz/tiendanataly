from django.contrib import admin, messages

from apps.core.admin_mixins import AuditedAdminMixin
from apps.core.audit import log_action
from apps.core.models import AuditLog

from . import services
from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("nombre_snapshot", "sku_snapshot", "precio_unitario", "cantidad")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class OrderHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    fields = ("creado_en", "estado_anterior", "estado_nuevo", "usuario", "nota")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


def _make_action(estado, label):
    @admin.action(description=label, permissions=["change"])
    def action(modeladmin, request, queryset):
        done = 0
        for order in queryset:
            try:
                services.transition(order, estado, user=request.user, nota="Desde el admin")
            except services.OrderError as exc:
                modeladmin.message_user(request, f"Pedido {order.pk}: {exc}", messages.ERROR)
                continue
            log_action(request, AuditLog.Accion.ACCION, order, cambios={"estado": estado})
            done += 1
        if done:
            modeladmin.message_user(request, f"{done} pedido(s) → {estado}.", messages.SUCCESS)

    action.__name__ = f"marcar_{estado.lower()}"
    return action


@admin.register(Order)
class OrderAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "creado_en", "cliente", "estado", "tipo_venta", "total_pen", "metodo_entrega")
    list_filter = ("estado", "tipo_venta", "metodo_entrega")
    search_fields = ("id", "cliente__nombre", "cliente__telefono", "public_token")
    date_hierarchy = "creado_en"
    inlines = [OrderItemInline, OrderHistoryInline]
    list_select_related = ("cliente",)
    actions = [
        _make_action(Order.Estado.COMPRADO, "Marcar como COMPRADO"),
        _make_action(Order.Estado.EN_CAMINO, "Marcar como EN CAMINO"),
        _make_action(Order.Estado.EN_LIMA, "Marcar como EN LIMA"),
        _make_action(Order.Estado.ENTREGADO, "Marcar como ENTREGADO"),
        _make_action(Order.Estado.CANCELADO, "Cancelar pedido"),
    ]

    def get_readonly_fields(self, request, obj=None):
        # Solo las notas son editables; el estado cambia únicamente con las acciones (deja historial).
        return [f.name for f in Order._meta.fields if f.name != "notas"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
