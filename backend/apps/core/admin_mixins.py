from .audit import log_action
from .models import AuditLog


class AuditedAdminMixin:
    """Registra en AuditLog cada alta, cambio y baja hecha desde el admin."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            cambios = {f: [str(form.initial.get(f, "")), str(form.cleaned_data.get(f, ""))] for f in form.changed_data}
            log_action(request, AuditLog.Accion.EDITAR, obj, cambios=cambios)
        else:
            log_action(request, AuditLog.Accion.CREAR, obj)

    def delete_model(self, request, obj):
        log_action(request, AuditLog.Accion.ELIMINAR, obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            log_action(request, AuditLog.Accion.ELIMINAR, obj)
        super().delete_queryset(request, queryset)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            log_action(request, AuditLog.Accion.ELIMINAR, obj)
            obj.delete()
        for obj in instances:
            nuevo = obj.pk is None
            obj.save()
            log_action(request, AuditLog.Accion.CREAR if nuevo else AuditLog.Accion.EDITAR, obj)
        formset.save_m2m()
