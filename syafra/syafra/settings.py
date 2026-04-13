"""
Django settings for the Syafra project.

Single module: development defaults, production enforced via environment variables.
See `.env.example` for Render / production variables.
"""

import logging
import os
import sys
import warnings
from pathlib import Path
from urllib.parse import urlsplit

import dj_database_url

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from django.core.exceptions import ImproperlyConfigured

# -----------------------------------------------------------------------------
# Paths & env helpers
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, *, default: bool = False) -> bool:
    """Parse a truthy env var. Keyword-only *default* avoids mixing up (name, default) argument order."""
    val = os.environ.get(name)
    if val is None:
        return default
    s = str(val).strip().lower()
    if not s:
        return default
    return s in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or not str(val).strip():
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _csv(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


def _clean_host(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return raw
    if "://" in raw:
        raw = urlsplit(raw).netloc or raw
    return raw.strip().rstrip("/")


# -----------------------------------------------------------------------------
# Core security
# -----------------------------------------------------------------------------

_DEV_SECRET_KEY = "django-insecure-dev-key-change-in-production"
# Production: set SECRET_KEY in env (avoids security.W009 — long, random, not django-insecure-*).
# Generate: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = os.getenv("SECRET_KEY", _DEV_SECRET_KEY)
DEBUG = _env_bool("DEBUG", default=True)

if not DEBUG:
    if not os.getenv("SECRET_KEY") or SECRET_KEY == _DEV_SECRET_KEY:
        raise ImproperlyConfigured(
            "Set SECRET_KEY in the environment when DEBUG=False. Generate one with: "
            'python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
        )

# Default host list when ALLOWED_HOSTS env is unset (set comma-separated hosts on Render).
# Matches: ALLOWED_HOSTS = ["your-app.onrender.com"] in production without env.
_DEFAULT_ALLOWED_HOSTS = [
    "syafra.com",
    "www.syafra.com",
    "syafra.onrender.com",
]
_DEV_ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "testserver",
    ".railway.app",
    ".onrender.com",
    ".render.com",
]

_env_allowed = _csv("ALLOWED_HOSTS", "")
if _env_allowed:
    ALLOWED_HOSTS = _env_allowed
elif DEBUG:
    ALLOWED_HOSTS = _DEFAULT_ALLOWED_HOSTS + _DEV_ALLOWED_HOSTS
else:
    ALLOWED_HOSTS = list(_DEFAULT_ALLOWED_HOSTS)

# Login, checkout, and payment flows POST with CSRF; wrong/missing origins → 403.
# On Render set CSRF_TRUSTED_ORIGINS (comma-separated). Code default matches:
#   CSRF_TRUSTED_ORIGINS = ["https://your-app.onrender.com"]
_DEFAULT_CSRF_ORIGINS = [
    "https://syafra.com",
    "https://www.syafra.com",
    "https://syafra.onrender.com",
]
_DEV_CSRF_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://localhost",
]

_env_csrf = _csv("CSRF_TRUSTED_ORIGINS", "")
if DEBUG:
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_DEFAULT_CSRF_ORIGINS + _env_csrf + _DEV_CSRF_ORIGINS))
else:
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_DEFAULT_CSRF_ORIGINS + _env_csrf))

# Email / absolute URLs: https when not in local HTTP mode (overridable via env)
USE_HTTPS = _env_bool("USE_HTTPS", default=not DEBUG)

# -----------------------------------------------------------------------------
# Applications & middleware
# -----------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cloudinary",
    "cloudinary_storage",
    "products",
    "cart",
    "orders",
    "accounts",
    "sendgrid",
]

# WhiteNoise must sit directly after SecurityMiddleware — https://whitenoise.readthedocs.io/
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "syafra.middleware.RequestCorrelationIdMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "syafra.urls"
WSGI_APPLICATION = "syafra.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cart.context_processors.cart_context",
                "syafra.context_processors.global_context",
            ],
        },
    },
]

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
# Pick the engine from DATABASE_URL only. Do not infer "Render" from RENDER / RENDER_EXTERNAL_URL here:
# those are often copied into a local .env and cause false positives.
# On Render, link PostgreSQL so DATABASE_URL is set; local dev usually omits it and uses SQLite.
#
# Optional: SYAFRA_LOG_DB_CONFIG=true prints a safe one-line summary to stderr (engine + whether DATABASE_URL is set).

_db_logger = logging.getLogger(__name__)
_database_url = (os.environ.get("DATABASE_URL") or "").strip()

if _database_url:
    _db_ssl = _env_bool("DATABASE_SSL_REQUIRE", default=not DEBUG)
    DATABASES = {
        "default": dj_database_url.config(
            default=_database_url,
            conn_max_age=600,
            ssl_require=_db_ssl,
        )
    }
    if not DEBUG and DATABASES["default"].get("ENGINE") != "django.db.backends.postgresql":
        raise ImproperlyConfigured(
            "Production requires PostgreSQL via DATABASE_URL. "
            "Set DATABASE_URL to your Render Postgres connection string."
        )
    _db_logger.debug("Database: from DATABASE_URL (ssl_require=%s).", _db_ssl)
else:
    if not DEBUG:
        raise ImproperlyConfigured(
            "Set DATABASE_URL in the environment when DEBUG=False. "
            "Production must use PostgreSQL and must not fall back to SQLite."
        )
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {"timeout": 60, "check_same_thread": False},
        }
    }
    _db_logger.debug("Database: SQLite (DATABASE_URL not set).")

if _env_bool("SYAFRA_LOG_DB_CONFIG", default=False):
    _engine = DATABASES["default"].get("ENGINE", "?")
    _db_logger.info(
        "Syafra DB: ENGINE=%s DATABASE_URL=%s",
        _engine,
        "set" if _database_url else "not set",
    )
    print(
        f"[syafra settings] ENGINE={_engine} DATABASE_URL={'set' if _database_url else 'not set'}",
        file=sys.stderr,
    )

# -----------------------------------------------------------------------------
# Auth & i18n
# -----------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

# -----------------------------------------------------------------------------
# Static & media
# -----------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
    "SECURE": True,
    "PREFIX": "",
}
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
STORAGES = {
    "default": {
        "BACKEND": DEFAULT_FILE_STORAGE,
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

if DEBUG:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------------------------------------------------------
# HTTPS & browser security (single branch — no duplicate assignments later)
# -----------------------------------------------------------------------------

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_REFERRER_POLICY = None
    PERMISSIONS_POLICY = None
    SECURE_CROSS_ORIGIN_OPENER_POLICY = None
else:
    # runserver only speaks HTTP. With DEBUG=False, SECURE_SSL_REDIRECT used to default True and
    # browsers were sent to https://127.0.0.1:8000 → ERR_SSL_PROTOCOL_ERROR. Gunicorn on Render is unaffected.
    _manage_py_runserver = len(sys.argv) >= 2 and sys.argv[1] == "runserver"
    SECURE_SSL_REDIRECT = _env_bool(
        "SECURE_SSL_REDIRECT",
        default=not _manage_py_runserver,
    )
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = _env_int("SECURE_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY = {
        "geolocation": [],
        "microphone": [],
        "camera": [],
    }
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# -----------------------------------------------------------------------------
# Cache (Redis in production when REDIS_URL is set; else LocMem)
# -----------------------------------------------------------------------------

_REDIS_URL = os.getenv("REDIS_URL", "").strip()
if _REDIS_URL and not DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL,
            "KEY_PREFIX": "syafra",
            "TIMEOUT": _env_int("CACHE_TIMEOUT", 300),
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "syafra-cache",
            "TIMEOUT": 300,
            "OPTIONS": {"MAX_ENTRIES": 1000},
        }
    }

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

_LOG_TO_FILE = _env_bool("LOG_TO_FILE", default=DEBUG)

_log_handlers: dict = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "verbose",
    },
}
_orders_handlers = ["console"]
_email_handlers = ["console"]


def _try_add_file_handler(handler_name: str, relative_path: str, formatter: str, level=None):
    path = BASE_DIR / relative_path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8"):
            pass
    except OSError:
        return
    cfg = {
        "class": "logging.FileHandler",
        "filename": str(path),
        "formatter": formatter,
    }
    if level is not None:
        cfg["level"] = level
    _log_handlers[handler_name] = cfg


if _LOG_TO_FILE:
    _try_add_file_handler("file", "logs.log", "verbose")
    _try_add_file_handler("email_file", "email_errors.log", "email", level="ERROR")
    if "file" in _log_handlers:
        _orders_handlers.append("file")
    if "email_file" in _log_handlers:
        _email_handlers.insert(0, "email_file")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation_id": {
            "()": "syafra.logging_context.CorrelationIdFilter",
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {module} | correlation_id={correlation_id} | {message}",
            "style": "{",
        },
        "email": {
            "format": "{levelname} {asctime} {module} | correlation_id={correlation_id} | Email Error: {message}",
            "style": "{",
        },
    },
    "handlers": _log_handlers,
    "loggers": {
        "orders": {
            "handlers": _orders_handlers,
            "level": "INFO",
            "propagate": True,
        },
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.core.mail": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "syafra.email": {
            "handlers": _email_handlers,
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if not DEBUG else "DEBUG",
    },
}

for _handler in LOGGING["handlers"].values():
    _handler.setdefault("filters", []).append("correlation_id")

# -----------------------------------------------------------------------------
# Auth redirects
# -----------------------------------------------------------------------------

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# -----------------------------------------------------------------------------
# Email (SendGrid API - Production Safe)
# -----------------------------------------------------------------------------

SENDGRID_API_KEY = (os.getenv("SENDGRID_API_KEY") or "").strip()
SENDGRID_SENDER_EMAIL = (os.getenv("SENDGRID_SENDER_EMAIL") or "").strip()
SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY = (os.getenv("SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY") or "").strip()
SENDGRID_EVENT_WEBHOOK_MAX_AGE_SECONDS = _env_int("SENDGRID_EVENT_WEBHOOK_MAX_AGE_SECONDS", 300)
SENDGRID_EVENT_WEBHOOK_REQUIRE_SIGNATURE = _env_bool(
    "SENDGRID_EVENT_WEBHOOK_REQUIRE_SIGNATURE",
    default=not DEBUG,
)
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "sendgrid_sdk").strip() or "sendgrid_sdk"

# HARD FAIL if missing when direct SendGrid delivery is enabled
if EMAIL_BACKEND == "sendgrid_sdk" and not SENDGRID_API_KEY:
    raise Exception("SENDGRID_API_KEY is missing in environment variables")

if EMAIL_BACKEND == "sendgrid_sdk" and not SENDGRID_SENDER_EMAIL:
    raise Exception("SENDGRID_SENDER_EMAIL is missing (must be verified in SendGrid)")

# Public host only (no scheme), e.g. your-app.onrender.com — used in password-reset / auth emails and link context.
# Payment flows use request URLs where applicable; keep DOMAIN aligned with your live hostname.
DOMAIN = _clean_host(os.environ.get("DOMAIN", "127.0.0.1:8000" if DEBUG else "syafra.com"))
ORDER_ALERT_EMAILS = _csv("ORDER_ALERT_EMAILS", "")

DEFAULT_FROM_EMAIL = f"SYAFRA <{SENDGRID_SENDER_EMAIL or 'noreply@localhost'}>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL

EMAIL_TIMEOUT = 30
EMAIL_FAIL_SILENTLY = False
EMAIL_SIMPLE_RETRY_ATTEMPTS = _env_int("EMAIL_SIMPLE_RETRY_ATTEMPTS", 2)
EMAIL_SIMPLE_RETRY_BASE_DELAY_SECONDS = _env_int("EMAIL_SIMPLE_RETRY_BASE_DELAY_SECONDS", 1)

if _env_bool("SYAFRA_LOG_EMAIL_CONFIG", default=False):
    _db_logger.info(
        "Syafra email config | backend=%s | sendgrid_api_key=%s | sender=%s | webhook_public_key=%s | webhook_signature_required=%s",
        EMAIL_BACKEND,
        "set" if SENDGRID_API_KEY else "missing",
        SENDGRID_SENDER_EMAIL or "missing",
        "set" if SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY else "missing",
        SENDGRID_EVENT_WEBHOOK_REQUIRE_SIGNATURE,
    )

ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS = _env_int("ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS", 900)
ORDER_PAYMENT_RETRY_TIMEOUT_SECONDS = _env_int("ORDER_PAYMENT_RETRY_TIMEOUT_SECONDS", 900)
FORCE_EMAIL_RETRY = _env_bool("FORCE_EMAIL_RETRY", default=True)
ORDER_NOTIFICATION_SYNC_RETRY_ATTEMPTS = _env_int("ORDER_NOTIFICATION_SYNC_RETRY_ATTEMPTS", 2)
ORDER_ASYNC_NOTIFICATIONS_ENABLED = _env_bool(
    "ORDER_ASYNC_NOTIFICATIONS_ENABLED", default=False
)
ORDER_INSTANT_EMAIL_ENABLED = _env_bool("ORDER_INSTANT_EMAIL_ENABLED", default=True)

# -----------------------------------------------------------------------------
# Celery (optional async)
# -----------------------------------------------------------------------------

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "memory://"))
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    os.getenv("REDIS_URL", "cache+memory://"),
)
CELERY_TASK_ALWAYS_EAGER = _env_bool("CELERY_TASK_ALWAYS_EAGER", default=DEBUG)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = _env_int("CELERY_TASK_SOFT_TIME_LIMIT", 240)
CELERY_TASK_TIME_LIMIT = _env_int("CELERY_TASK_TIME_LIMIT", 300)
CELERY_TASK_DEFAULT_QUEUE = os.getenv("CELERY_TASK_DEFAULT_QUEUE", "default")
CELERY_NOTIFICATION_QUEUE = os.getenv("CELERY_NOTIFICATION_QUEUE", "notifications")
CELERY_TASK_ROUTES = {
    "orders.tasks.send_email_notification": {"queue": CELERY_NOTIFICATION_QUEUE},
    "orders.tasks.send_whatsapp_notification": {"queue": CELERY_NOTIFICATION_QUEUE},
}

# -----------------------------------------------------------------------------
# Payments & integrations
# -----------------------------------------------------------------------------

RAZORPAY_KEY_ID = (os.getenv("RAZORPAY_KEY_ID", "") or "").strip()
RAZORPAY_KEY_SECRET = (os.getenv("RAZORPAY_KEY_SECRET", "") or "").strip()
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

if os.getenv("RENDER") and not RAZORPAY_WEBHOOK_SECRET:
    raise ImproperlyConfigured(
        "RAZORPAY_WEBHOOK_SECRET must be set in production"
    )

WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "919037626684")
WHATSAPP_DEFAULT_MESSAGE = os.getenv(
    "WHATSAPP_DEFAULT_MESSAGE",
    "Hi, I am interested in your products. Please share more details.",
)

# -----------------------------------------------------------------------------
# Production validation (after DATABASES and EMAIL_BACKEND exist)
# -----------------------------------------------------------------------------

if not DEBUG:
    _missing = []
    if not os.getenv("CLOUDINARY_CLOUD_NAME"):
        _missing.append("CLOUDINARY_CLOUD_NAME")
    if not os.getenv("CLOUDINARY_API_KEY"):
        _missing.append("CLOUDINARY_API_KEY")
    if not os.getenv("CLOUDINARY_API_SECRET"):
        _missing.append("CLOUDINARY_API_SECRET")
    if not RAZORPAY_KEY_ID or RAZORPAY_KEY_ID in ("", "your_razorpay_key_id"):
        _missing.append("RAZORPAY_KEY_ID")
    if not RAZORPAY_KEY_SECRET or RAZORPAY_KEY_SECRET in ("", "your_razorpay_key_secret"):
        _missing.append("RAZORPAY_KEY_SECRET")
    if _missing:
        raise ImproperlyConfigured(
            f"Production requires: {', '.join(_missing)}. "
            "Set these in the environment or .env file."
        )

    if "console" in EMAIL_BACKEND and not _env_bool(
        "ALLOW_CONSOLE_EMAIL_IN_PRODUCTION", default=False
    ):
        raise ImproperlyConfigured(
            "Production is using the console email backend (no delivery). "
            "Configure the direct SendGrid integration. (ALLOW_CONSOLE_EMAIL_IN_PRODUCTION=true is staging-only - remove for real launch.)"
        )

    if DOMAIN in ("127.0.0.1:8000", "127.0.0.1", "localhost:8000", "localhost"):
        warnings.warn(
            "DOMAIN is still a development default. Set DOMAIN in the environment to your public host "
            "(e.g. your-app.onrender.com) so password-reset and other email links point at the real site.",
            UserWarning,
            stacklevel=2,
        )

    if SENDGRID_EVENT_WEBHOOK_REQUIRE_SIGNATURE and not SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY:
        raise ImproperlyConfigured(
            "SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY must be set in production when "
            "SENDGRID_EVENT_WEBHOOK_REQUIRE_SIGNATURE is enabled."
        )

    if not SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY:
        warnings.warn(
            "SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY is not set. SendGrid event webhooks cannot be signature-verified "
            "until you configure the public key from SendGrid Mail Settings.",
            UserWarning,
            stacklevel=2,
        )

    if SECURE_SSL_REDIRECT and not CSRF_TRUSTED_ORIGINS:
        warnings.warn(
            "CSRF_TRUSTED_ORIGINS is empty while SECURE_SSL_REDIRECT is enabled — "
            "logins, forms, and payments will fail CSRF checks. "
            "Set CSRF_TRUSTED_ORIGINS (e.g. https://your-app.onrender.com).",
            UserWarning,
            stacklevel=2,
        )
