from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
# En producción HSTS nunca queda en 0 aunque el .env lo traiga así.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000) or 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
ADMIN_REQUIRE_2FA = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
