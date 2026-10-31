"""Aviso de errores a Sentry (opcional): enterarse de una falla antes de que lo note una clienta.

Sin SENTRY_DSN no se envía nada. Con DSN solo viajan los errores, sin datos personales:
no se manda IP, cookies ni usuario, y nunca el cuerpo de las peticiones (nombres, teléfonos,
direcciones y comprobantes de pago).
"""


def init_sentry(dsn, *, environment="production", release=""):
    """Activa Sentry si hay DSN. Devuelve True si quedó activo."""
    if not dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release or None,
        send_default_pii=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,  # solo errores; las trazas de rendimiento gastan la cuota del plan gratuito
    )
    return True
