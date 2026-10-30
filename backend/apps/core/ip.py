from django.conf import settings


def client_ip(request, credentials=None):
    """IP real de quien hace la petición.

    Detrás del proxy (Caddy) se usa la ÚLTIMA dirección de X-Forwarded-For: es la que el proxy vio y
    no puede falsificar el cliente (lo que el cliente mande queda a la izquierda). Sin proxy (desarrollo)
    se usa REMOTE_ADDR. Se usa también para el bloqueo por intentos fallidos y el rate limiting.
    """
    if settings.BEHIND_PROXY:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[-1].strip() or None
    return request.META.get("REMOTE_ADDR") or None
