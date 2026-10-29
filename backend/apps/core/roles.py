"""Roles de la tienda como grupos de Django.

La Administradora (dueña) y el Staff NO son superusuarios. El superusuario
técnico es solo el desarrollador.
"""
from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission

ADMINISTRADORA = "Administradora"
STAFF = "Staff"

CRUD = ("add", "change", "delete", "view")
VER = ("view",)
VER_EDITAR = ("view", "change")
ALTA_EDICION = ("add", "change", "view")

# (app_label, modelo en minúsculas) -> acciones
ROLE_PERMISSIONS = {
    ADMINISTRADORA: {
        ("catalog", "category"): CRUD,
        ("catalog", "brand"): CRUD,
        ("catalog", "collection"): CRUD,
        ("catalog", "product"): CRUD,
        ("catalog", "productvariant"): CRUD,
        ("catalog", "productimage"): CRUD,
        ("catalog", "review"): ("view", "change", "delete"),
        ("catalog", "stockalert"): VER,
        ("inventory", "inventorymovement"): VER,
        ("inventory", "stockreservation"): VER,
        ("orders", "order"): VER_EDITAR,
        ("orders", "orderitem"): VER,
        ("orders", "orderstatushistory"): VER,
        ("payments", "payment"): VER_EDITAR,
        ("payments", "paymentevent"): VER,
        ("payments", "bankaccount"): CRUD,
        ("accounts", "customer"): VER_EDITAR,
        ("accounts", "address"): VER,
        ("accounts", "consent"): VER,
        ("core", "storesettings"): VER_EDITAR,
        ("core", "exchangerate"): CRUD,
        ("core", "auditlog"): VER,
        ("shipping", "shippingzone"): CRUD,
        ("legal", "complaint"): VER_EDITAR,
        ("integrations", "webhookoutbox"): VER,
    },
    STAFF: {
        ("catalog", "category"): VER,
        ("catalog", "brand"): VER,
        ("catalog", "collection"): VER,
        ("catalog", "product"): ALTA_EDICION,
        ("catalog", "productvariant"): ALTA_EDICION,
        ("catalog", "productimage"): CRUD,
        ("catalog", "review"): VER_EDITAR,
        ("inventory", "inventorymovement"): VER,
        ("orders", "order"): VER_EDITAR,
        ("orders", "orderitem"): VER,
        ("orders", "orderstatushistory"): VER,
        ("shipping", "shippingzone"): VER,
    },
}

# Permisos personalizados (codename completo "app.codename")
EXTRA_PERMISSIONS = {
    ADMINISTRADORA: ["catalog.ver_finanzas"],
    STAFF: [],
}


def setup_roles():
    """Crea/actualiza los grupos con sus permisos. Idempotente."""
    for app_config in global_apps.get_app_configs():
        create_permissions(app_config, verbosity=0)

    for role, spec in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        perms = []
        for (app_label, model), actions in spec.items():
            for action in actions:
                perms.append(Permission.objects.get(content_type__app_label=app_label, codename=f"{action}_{model}"))
        for full in EXTRA_PERMISSIONS[role]:
            app_label, codename = full.split(".")
            perms.append(Permission.objects.get(content_type__app_label=app_label, codename=codename))
        group.permissions.set(perms)
