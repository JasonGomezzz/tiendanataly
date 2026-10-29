from django.contrib import admin

from .admin_mixins import AuditedAdminMixin
from .models import AuditLog, ExchangeRate, StoreSettings


@admin.register(StoreSettings)
class StoreSettingsAdmin(AuditedAdminMixin, admin.ModelAdmin):
    fieldsets = (
        ("Tienda", {"fields": ("nombre_tienda", "whatsapp", "aviso_legal")}),
        ("Precios", {"fields": ("costo_envio_default", "envio_estimado_usd", "impuestos_estimados_pct", "margen_default", "pct_comision", "redondeo_multiplo")}),
        ("Pedidos por encargo y reservas", {"fields": ("pct_adelanto", "minutos_reserva")}),
        ("Pagos Yape / Plin", {"fields": ("yape_numero", "yape_titular", "plin_numero", "plin_titular")}),
    )

    def has_add_permission(self, request):
        return not StoreSettings.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        StoreSettings.load()
        return super().changelist_view(request, extra_context)


@admin.register(ExchangeRate)
class ExchangeRateAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("vigente_desde", "usd_pen", "creado_por")
    readonly_fields = ("creado_por",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("creado_en", "usuario", "accion", "modelo", "objeto_repr")
    list_filter = ("accion", "modelo")
    search_fields = ("objeto_repr", "usuario__username")
    date_hierarchy = "creado_en"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
