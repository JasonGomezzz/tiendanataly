from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.core.admin_mixins import AuditedAdminMixin

from .models import Address, Consent, Customer, User


@admin.register(User)
class UserAdmin(AuditedAdminMixin, DjangoUserAdmin):
    """Solo el superusuario técnico gestiona usuarios (los grupos no incluyen auth.user)."""

    list_display = ("username", "email", "is_staff", "is_active", "last_login")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    fieldsets = DjangoUserAdmin.fieldsets + (("Contacto", {"fields": ("telefono",)}),)


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0


class ConsentInline(admin.TabularInline):
    model = Consent
    extra = 0
    readonly_fields = ("tipo", "version", "aceptado_en", "ip")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Customer)
class CustomerAdmin(AuditedAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "telefono", "email", "creado_en", "anonimizado")
    search_fields = ("nombre", "telefono", "email")
    inlines = [AddressInline, ConsentInline]
    readonly_fields = ("user", "anonimizado")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("customer", "distrito", "direccion")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ("customer", "tipo", "version", "aceptado_en")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
