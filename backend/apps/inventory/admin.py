from django.contrib import admin

from .models import InventoryMovement, StockReservation


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InventoryMovement)
class InventoryMovementAdmin(ReadOnlyAdmin):
    list_display = ("creado_en", "variante", "tipo", "delta_disponible", "delta_reservado", "motivo", "usuario")
    list_filter = ("tipo",)
    search_fields = ("variante__sku", "variante__producto__nombre", "motivo")
    date_hierarchy = "creado_en"


@admin.register(StockReservation)
class StockReservationAdmin(ReadOnlyAdmin):
    list_display = ("variante", "cantidad", "estado", "expira_en", "pedido")
    list_filter = ("estado",)
