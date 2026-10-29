from .models import AuditLog

SENSITIVE = ("password", "token", "secret", "key")


def _client_ip(request):
    return request.META.get("REMOTE_ADDR") or None


def _clean(changes):
    cleaned = {}
    for field, value in (changes or {}).items():
        if any(s in field.lower() for s in SENSITIVE):
            cleaned[field] = "***"
        else:
            cleaned[field] = value if isinstance(value, (int, float, bool, type(None), dict, list)) else str(value)
    return cleaned


def log_action(request, accion, obj=None, *, modelo=None, cambios=None):
    """Registra una acción del admin. `accion` es un valor de AuditLog.Accion."""
    user = getattr(request, "user", None)
    return AuditLog.objects.create(
        usuario=user if user is not None and user.is_authenticated else None,
        accion=accion,
        modelo=modelo or (obj._meta.label if obj is not None else ""),
        objeto_id=str(obj.pk) if obj is not None and obj.pk is not None else "",
        objeto_repr=str(obj)[:255] if obj is not None else "",
        cambios=_clean(cambios),
        ip=_client_ip(request),
    )
