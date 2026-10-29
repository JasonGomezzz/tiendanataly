import os

os.environ.setdefault("DJANGO_SECRET_KEY", "clave-solo-para-tests")
os.environ.setdefault("POSTGRES_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "tiendanataly"))

from .base import *  # noqa: E402,F401,F403
from .base import REST_FRAMEWORK  # noqa: E402

DEBUG = False

# TEST_DB=sqlite permite correr casi toda la suite sin Postgres. El test de concurrencia
# (select_for_update) se omite en SQLite y se ejecuta de verdad en Postgres.
if os.environ.get("TEST_DB") == "sqlite":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ADMIN_REQUIRE_2FA = False
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_ROOT = "/tmp/tiendanataly-test-media"

# Tasas altas para que los tests no se estorben; test_throttling las baja a propósito.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {k: "1000/min" for k in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]},
}
OTP_TOTP_THROTTLE_FACTOR = 0
