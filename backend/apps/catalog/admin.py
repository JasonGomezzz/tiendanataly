from django import forms
from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.utils.html import format_html

from apps.core.admin_mixins import AuditedAdminMixin
from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.inventory import services as stock

from .models import Brand, Category, Collection, Product, ProductImage, ProductVariant, Review, StockAlert

FINANCE_FIELDS = ("precio_compra_usd", "margen", "precio_venta_pen", "oferta_cantidad", "oferta_precio")


def thumbnail(image, size=56):
    if not image:
        return "—"
    return format_html('<img src="{}" style="height:{}px;width:{}px;object-fit:cover;border-radius:4px" alt="">', image.url, size, size)


@admin.register(Category)
class CategoryAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden")
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(Brand)
class BrandAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "slug")
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(Collection)
class CollectionAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "activa", "orden")
    prepopulated_fields = {"slug": ("nombre",)}
    filter_horizontal = ("productos",)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("preview", "imagen", "alt", "orden")
    readonly_fields = ("preview",)

    @admin.display(description="vista previa")
    def preview(self, obj):
        return thumbnail(obj.imagen) if obj.pk else "—"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("sku", "nombre", "atributo", "stock_disponible", "stock_reservado", "activo")
    readonly_fields = ("stock_disponible", "stock_reservado")


class AjusteStockForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput, required=False)
    tipo = forms.ChoiceField(
        choices=[("entrada", "Ingreso de mercadería (suma)"), ("ajuste", "Corrección de inventario (suma o resta)")],
    )
    cantidad = forms.IntegerField(help_text="En corrección puede ser negativa.")
    motivo = forms.CharField(min_length=3, max_length=200, help_text="Obligatorio; queda en el historial.")

    def clean(self):
        data = super().clean()
        if data.get("tipo") == "entrada" and data.get("cantidad") is not None and data["cantidad"] <= 0:
            self.add_error("cantidad", "Un ingreso debe ser mayor que cero.")
        if data.get("cantidad") == 0:
            self.add_error("cantidad", "La cantidad no puede ser cero.")
        return data


@admin.register(Product)
class ProductAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_filter = ("estado", "tipo_venta", "marca", "categoria")
    search_fields = ("nombre", "slug", "variantes__sku")
    prepopulated_fields = {"slug": ("nombre",)}
    inlines = [ProductVariantInline, ProductImageInline]
    actions = ["publicar", "ocultar"]
    list_per_page = 30
    fieldsets = (
        (None, {"fields": ("nombre", "slug", "marca", "categoria", "linea", "estado", "tipo_venta", "orden")}),
        ("Contenido", {"fields": ("descripcion", "detalles")}),
        ("Precios y costos", {"fields": FINANCE_FIELDS}),
        ("Interno", {"fields": ("notas_internas",)}),
    )

    def _can_see_finance(self, request):
        return request.user.has_perm("catalog.ver_finanzas")

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if self._can_see_finance(request):
            return fieldsets
        return [fs for fs in fieldsets if fs[0] != "Precios y costos"]

    def get_list_display(self, request):
        cols = ["miniatura", "nombre", "marca", "categoria", "estado", "stock", "aviso_imagen"]
        if self._can_see_finance(request):
            cols.insert(5, "precio_venta_pen")
        return cols

    @admin.display(description="foto")
    def miniatura(self, obj):
        first = obj.imagenes.first()
        return thumbnail(first.imagen) if first else "—"

    @admin.display(description="stock")
    def stock(self, obj):
        return obj.stock_total_disponible

    @admin.display(description="imagen", boolean=True)
    def aviso_imagen(self, obj):
        return not obj.sin_imagen

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("marca", "categoria").prefetch_related("variantes", "imagenes")

    @admin.action(description="Publicar seleccionados (requiere precio de venta)", permissions=["change"])
    def publicar(self, request, queryset):
        publicados = 0
        for product in queryset:
            if not product.precio_venta_pen:
                self.message_user(request, f"«{product.nombre}» no tiene precio de venta: sigue en borrador.", messages.WARNING)
                continue
            product.estado = Product.Estado.PUBLICADO
            product.save(update_fields=["estado", "actualizado_en"])
            product.sync_agotado()
            log_action(request, AuditLog.Accion.ACCION, product, cambios={"accion": "publicar"})
            publicados += 1
        if publicados:
            self.message_user(request, f"{publicados} producto(s) publicado(s).", messages.SUCCESS)

    @admin.action(description="Ocultar seleccionados (pasar a borrador)", permissions=["change"])
    def ocultar(self, request, queryset):
        for product in queryset:
            log_action(request, AuditLog.Accion.ACCION, product, cambios={"accion": "ocultar"})
        n = queryset.update(estado=Product.Estado.BORRADOR)
        self.message_user(request, f"{n} producto(s) ocultado(s).", messages.SUCCESS)


@admin.register(ProductVariant)
class ProductVariantAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("producto", "nombre", "sku", "stock_disponible", "stock_reservado", "activo")
    list_filter = ("atributo", "activo", "producto__estado")
    search_fields = ("sku", "nombre", "producto__nombre")
    readonly_fields = ("stock_disponible", "stock_reservado")
    actions = ["ajustar_stock"]

    @admin.action(description="Ajustar stock (con motivo)", permissions=["change"])
    def ajustar_stock(self, request, queryset):
        if "apply" in request.POST:
            form = AjusteStockForm(request.POST)
            if form.is_valid():
                tipo, cantidad, motivo = form.cleaned_data["tipo"], form.cleaned_data["cantidad"], form.cleaned_data["motivo"]
                try:
                    for variant in queryset:
                        if tipo == "entrada":
                            stock.add_stock(variant, cantidad, motivo, user=request.user)
                        else:
                            stock.adjust_stock(variant, cantidad, motivo, user=request.user)
                        log_action(request, AuditLog.Accion.ACCION, variant, cambios={"accion": "ajustar_stock", "tipo": tipo, "cantidad": cantidad, "motivo": motivo})
                except stock.StockError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
                else:
                    self.message_user(request, "Stock actualizado.", messages.SUCCESS)
                    return None
        else:
            form = AjusteStockForm(initial={"_selected_action": list(queryset.values_list("pk", flat=True))})
        context = {**self.admin_site.each_context(request), "form": form, "variants": queryset, "title": "Ajustar stock", "opts": self.model._meta, "action_name": "ajustar_stock"}
        return TemplateResponse(request, "admin/catalog/ajustar_stock.html", context)


@admin.register(Review)
class ReviewAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("producto", "autor", "puntaje", "estado", "creado_en")
    list_filter = ("estado", "puntaje")
    actions = ["aprobar", "rechazar"]
    readonly_fields = ("producto", "cliente", "autor", "puntaje", "comentario", "foto")

    def has_add_permission(self, request):
        return False

    @admin.action(description="Aprobar reseñas", permissions=["change"])
    def aprobar(self, request, queryset):
        queryset.update(estado=Review.Estado.APROBADA)

    @admin.action(description="Rechazar reseñas", permissions=["change"])
    def rechazar(self, request, queryset):
        queryset.update(estado=Review.Estado.RECHAZADA)


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ("variante", "email", "telefono", "notificado", "creado_en")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
