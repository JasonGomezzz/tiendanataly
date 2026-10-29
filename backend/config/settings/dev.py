from .base import *  # noqa: F401,F403

DEBUG = True

CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS or ["http://localhost:3000"]  # noqa: F405
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS or ["http://localhost:3000"]  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
