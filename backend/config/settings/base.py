from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "apps.core.apps.TiendaAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "axes",
    "corsheaders",
    "csp",
    "rest_framework",
    "django_filters",
    "apps.core.apps.CoreConfig",
    "apps.accounts",
    "apps.catalog",
    "apps.inventory",
    "apps.pricing",
    "apps.cart",
    "apps.orders",
    "apps.payments",
    "apps.shipping",
    "apps.legal",
    "apps.integrations.apps.IntegrationsConfig",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "apps.core.middleware.PermissionsPolicyMiddleware",
    "axes.middleware.AxesMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="tiendanataly"),
        "USER": env("POSTGRES_USER", default="tiendanataly"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Sesión y CSRF (cookies HttpOnly; nunca tokens en localStorage) ---------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# --- Headers de seguridad ---------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "img-src": ["'self'", "data:", "https://res.cloudinary.com"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "script-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    }
}

# --- Subidas ----------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}

# --- Admin / 2FA ------------------------------------------------------------
ADMIN_URL_PATH = env("ADMIN_URL_PATH", default="panel-nataly-cambiar/")
ADMIN_REQUIRE_2FA = env.bool("ADMIN_REQUIRE_2FA", default=False)
OTP_TOTP_ISSUER = env("STORE_NAME", default="Marle Fashion")

# --- Bloqueo por intentos fallidos (django-axes) -----------------------------
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [["ip_address", "username"]]
AXES_RESET_ON_SUCCESS = True
# Detrás de Caddy todos llegarían con la IP del proxy y un atacante bloquearía a todas las clientas:
# se usa la IP real (ver apps/core/ip.py).
BEHIND_PROXY = env.bool("BEHIND_PROXY", default=False)
AXES_CLIENT_IP_CALLABLE = "apps.core.ip.client_ip"

# --- DRF --------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "NUM_PROXIES": 1 if env.bool("BEHIND_PROXY", default=False) else 0,
    # Límites por IP. Se pueden subir por entorno solo para pruebas de carga (THROTTLE_<NOMBRE>=1000/min).
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="120/min"),
        "user": env("THROTTLE_USER", default="240/min"),
        "login": env("THROTTLE_LOGIN", default="10/min"),
        "register": env("THROTTLE_REGISTER", default="5/min"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", default="5/hour"),
        "checkout": env("THROTTLE_CHECKOUT", default="10/min"),
        "complaint": env("THROTTLE_COMPLAINT", default="5/hour"),
    },
}

# --- Celery -----------------------------------------------------------------
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = False

# --- Negocio ----------------------------------------------------------------
STORE_NAME = env("STORE_NAME", default="Marle Fashion")
SITE_URL = env("NEXT_PUBLIC_SITE_URL", default="http://localhost:3000").rstrip("/")

# Correo (recuperar contraseña). En desarrollo se imprime en consola.
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Marle Fashion <no-responder@localhost>")
STORE_WHATSAPP = env("STORE_WHATSAPP", default="")
PAYMENTS_PROVIDER = env("PAYMENTS_PROVIDER", default="manual_yape_plin")
# Culqi. La clave secreta solo vive en el backend. CULQI_API_BASE y la unidad del monto (céntimos)
# deben confirmarse contra el sandbox antes de salir a producción (ver docs/pagos-culqi.md).
CULQI_PUBLIC_KEY = env("CULQI_PUBLIC_KEY", default="")
CULQI_SECRET_KEY = env("CULQI_SECRET_KEY", default="")
CULQI_API_BASE = env("CULQI_API_BASE", default="https://api.culqi.com/v2")
CULQI_WEBHOOK_SECRET = env("CULQI_WEBHOOK_SECRET", default="")
CULQI_WEBHOOK_BASIC_USER = env("CULQI_WEBHOOK_BASIC_USER", default="")
CULQI_WEBHOOK_BASIC_PASSWORD = env("CULQI_WEBHOOK_BASIC_PASSWORD", default="")
FRONTEND_URL = env("FRONTEND_URL", default="http://frontend:3000")
REVALIDATE_SECRET = env("REVALIDATE_SECRET", default="")
N8N_WEBHOOK_URL = env("N8N_WEBHOOK_URL", default="")
N8N_WEBHOOK_SECRET = env("N8N_WEBHOOK_SECRET", default="")
SEED_DIR = Path(env("SEED_DIR", default="/seed"))
# Sirve /media desde Django (el optimizador de imágenes de Next lo pide por dentro). Caddy los sirve al público.
SERVE_MEDIA = env.bool("SERVE_MEDIA", default=False)

# IGV vigente en Perú, usado al calcular comisiones de pasarela.
IGV_RATE = "0.18"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
