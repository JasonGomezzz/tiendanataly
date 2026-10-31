from config.observability import init_sentry

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
# En producción HSTS nunca queda en 0 aunque el .env lo traiga así.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000) or 31536000
# Los archivos públicos y el healthcheck se piden por la red interna sin pasar por Caddy (sin HTTPS).
SECURE_REDIRECT_EXEMPT = [r"^media/", r"^health/"]
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
ADMIN_REQUIRE_2FA = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Avisos de errores (opcional; ver docs/despliegue.md). Sin SENTRY_DSN queda apagado.
init_sentry(env("SENTRY_DSN", default=""), environment=env("SENTRY_ENVIRONMENT", default="production"))
