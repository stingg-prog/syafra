"""
Django settings for syafra project.

Production-ready settings with environment variable support.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Dev-only default; production must override via environment (validated below when DEBUG=False).
_INSECURE_DEV_SECRET_KEY = 'django-insecure-dev-key-change-in-production'
SECRET_KEY = os.getenv('SECRET_KEY', _INSECURE_DEV_SECRET_KEY)

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

if not DEBUG:
    if not os.getenv('SECRET_KEY') or SECRET_KEY == _INSECURE_DEV_SECRET_KEY:
        raise ImproperlyConfigured(
            'Set a unique SECRET_KEY in the environment when DEBUG=False.'
        )

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv(
        'ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver,.railway.app,.render.com'
    ).split(',') if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'false' if DEBUG else 'true').lower() in ('1', 'true', 'yes')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'products',
    'cart',
    'orders',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'syafra.middleware.RequestCorrelationIdMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'syafra.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.csrf',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart_context',
                'syafra.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'syafra.wsgi.application'

# Database Configuration
# Priority: DATABASE_URL (Render/Railway) > DB_ENGINE > SQLite (development)

DATABASE_URL = os.getenv('DATABASE_URL', '')

if DATABASE_URL:
    # Use dj-database-url for Render/Railway PostgreSQL
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    db_engine = os.getenv('DB_ENGINE', 'django.db.backends.sqlite3')
    if db_engine == 'django.db.backends.postgresql':
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.getenv('DB_NAME', 'syafra'),
                'USER': os.getenv('DB_USER', 'postgres'),
                'PASSWORD': os.getenv('DB_PASSWORD', ''),
                'HOST': os.getenv('DB_HOST', 'localhost'),
                'PORT': os.getenv('DB_PORT', '5432'),
            }
        }
    elif db_engine == 'django.db.backends.mysql':
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': os.getenv('DB_NAME', 'syafra'),
                'USER': os.getenv('DB_USER', 'root'),
                'PASSWORD': os.getenv('DB_PASSWORD', ''),
                'HOST': os.getenv('DB_HOST', 'localhost'),
                'PORT': os.getenv('DB_PORT', '3306'),
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
                'OPTIONS': {
                    'timeout': 30,
                },
            }
        }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# File logging is optional: many PaaS disks are ephemeral or read-only. Default file logs on DEBUG only.
_LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true' if DEBUG else 'false').lower() in ('1', 'true', 'yes')

_log_handlers = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
    },
}
_orders_handlers = ['console']
_email_handlers = ['console']


def _try_add_file_handler(handler_name, relative_path, formatter, level=None):
    """Attach a FileHandler only if the path is writable (skip silently on failure)."""
    path = BASE_DIR / relative_path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8'):
            pass
    except OSError:
        return
    cfg = {
        'class': 'logging.FileHandler',
        'filename': str(path),
        'formatter': formatter,
    }
    if level is not None:
        cfg['level'] = level
    _log_handlers[handler_name] = cfg


if _LOG_TO_FILE:
    _try_add_file_handler('file', 'logs.log', 'verbose')
    _try_add_file_handler('email_file', 'email_errors.log', 'email', level='ERROR')
    if 'file' in _log_handlers:
        _orders_handlers.append('file')
    if 'email_file' in _log_handlers:
        _email_handlers.insert(0, 'email_file')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'correlation_id': {
            '()': 'syafra.logging_context.CorrelationIdFilter',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {module} | correlation_id={correlation_id} | {message}',
            'style': '{',
        },
        'email': {
            'format': '{levelname} {asctime} {module} | correlation_id={correlation_id} | Email Error: {message}',
            'style': '{',
        },
        # 🔒 SECURITY FIX: Add security logging formatter
        'security': {
            'format': '[SECURITY] {levelname} {asctime} {name} | correlation_id={correlation_id} | {message}',
            'style': '{',
        },
    },
    'handlers': _log_handlers,
    'loggers': {
        'orders': {
            'handlers': _orders_handlers,
            'level': 'INFO',
            'propagate': True,
        },
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            # 🔒 SECURITY FIX: Enhanced logging for security events
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'syafra.email': {
            'handlers': _email_handlers,
            'level': 'INFO',
            'propagate': False,
        },
    },
}

for _handler in LOGGING['handlers'].values():
    _handler.setdefault('filters', []).append('correlation_id')

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'products:home'
LOGOUT_REDIRECT_URL = 'products:home'

# ===================================================================
# EMAIL CONFIGURATION - PRODUCTION READY
# ===================================================================

# Email Service: 'sendgrid', 'gmail', or 'console'
EMAIL_SERVICE = os.getenv('EMAIL_SERVICE', 'console')

# Domain for password reset links
DOMAIN = os.getenv('DOMAIN', '127.0.0.1:8000')

# ===================================================================
# SENDGRID SMTP CONFIGURATION (RECOMMENDED FOR PRODUCTION)
# ===================================================================
# SendGrid uses SMTP for reliable, fast email delivery
# Required environment variables:
#   EMAIL_SERVICE=sendgrid
#   SENDGRID_API_KEY=SG.your_api_key_here
#   SENDGRID_SENDER_EMAIL=your_verified_sender@yourdomain.com
#
# SendGrid SMTP details:
#   Host: smtp.sendgrid.net
#   Port: 587 (TLS)
#   Username: apikey (always this, not your SendGrid username)
#   Password: Your SendGrid API key (starts with SG.)

if EMAIL_SERVICE == 'sendgrid':
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
    SENDGRID_SENDER_EMAIL = os.getenv('SENDGRID_SENDER_EMAIL', 'noreply@yourdomain.com')
    
    if SENDGRID_API_KEY:
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = 'smtp.sendgrid.net'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_HOST_USER = 'apikey'
        EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
        DEFAULT_FROM_EMAIL = f'SYAFRA <{SENDGRID_SENDER_EMAIL}>'
        EMAIL_FAIL_SILENTLY = False
    else:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
        DEFAULT_FROM_EMAIL = 'SYAFRA <noreply@localhost>'

# ===================================================================
# GMAIL SMTP CONFIGURATION (DEVELOPMENT ONLY)
# ===================================================================
# For development/testing with Gmail SMTP
elif EMAIL_SERVICE == 'gmail':
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes')
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        DEFAULT_FROM_EMAIL = f'SYAFRA <{EMAIL_HOST_USER}>'
        EMAIL_FAIL_SILENTLY = False
    else:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
        DEFAULT_FROM_EMAIL = 'SYAFRA <noreply@localhost>'

# ===================================================================
# CONSOLE BACKEND (DEFAULT/DEVELOPMENT)
# ===================================================================
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'SYAFRA <noreply@localhost>'
    EMAIL_FAIL_SILENTLY = False

# ===================================================================
# EMAIL DELIVERY SETTINGS - INSTANT DELIVERY (NO DELAYS)
# ===================================================================
# IMPORTANT: These settings ensure emails are sent IMMEDIATELY without Celery delays

SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_TIMEOUT = 30
EMAIL_FAIL_SILENTLY = False  # Always fail loudly for debugging

# Claim timeout for email deduplication (seconds)
ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS = int(os.getenv('ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS', '900'))
ORDER_PAYMENT_RETRY_TIMEOUT_SECONDS = int(os.getenv('ORDER_PAYMENT_RETRY_TIMEOUT_SECONDS', '900'))

# Force retry for stuck email claims
FORCE_EMAIL_RETRY = os.getenv('FORCE_EMAIL_RETRY', 'true').lower() in ('1', 'true', 'yes')

# Sync retry attempts for transient failures
ORDER_NOTIFICATION_SYNC_RETRY_ATTEMPTS = int(os.getenv('ORDER_NOTIFICATION_SYNC_RETRY_ATTEMPTS', '2'))

# DISABLED: Async notifications via Celery (emails are now synchronous)
ORDER_ASYNC_NOTIFICATIONS_ENABLED = os.getenv('ORDER_ASYNC_NOTIFICATIONS_ENABLED', 'false').lower() in ('1', 'true', 'yes')

# ENABLED: Instant email delivery (no transaction.on_commit delay)
ORDER_INSTANT_EMAIL_ENABLED = os.getenv('ORDER_INSTANT_EMAIL_ENABLED', 'true').lower() in ('1', 'true', 'yes')

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'memory://'))
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', os.getenv('REDIS_URL', 'cache+memory://'))
CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'false').lower() in ('1', 'true', 'yes')
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', '240'))
CELERY_TASK_TIME_LIMIT = int(os.getenv('CELERY_TASK_TIME_LIMIT', '300'))
CELERY_TASK_DEFAULT_QUEUE = os.getenv('CELERY_TASK_DEFAULT_QUEUE', 'default')
CELERY_NOTIFICATION_QUEUE = os.getenv('CELERY_NOTIFICATION_QUEUE', 'notifications')
CELERY_TASK_ROUTES = {
    'orders.tasks.send_email_notification': {'queue': CELERY_NOTIFICATION_QUEUE},
    'orders.tasks.send_whatsapp_notification': {'queue': CELERY_NOTIFICATION_QUEUE},
}

LOGGING['loggers']['django.core.mail'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}

# Razorpay keys are loaded from PaymentSettings in the database (admin). Env vars here are unused
# but kept for documentation / future sync scripts.
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')

# Production validation: Ensure required keys are configured
if not DEBUG:
    missing_keys = []
    if not RAZORPAY_KEY_ID or RAZORPAY_KEY_ID in ('', 'your_razorpay_key_id', 'your_razorpay_key_secret'):
        missing_keys.append('RAZORPAY_KEY_ID')
    if not RAZORPAY_KEY_SECRET or RAZORPAY_KEY_SECRET in ('', 'your_razorpay_key_id', 'your_razorpay_key_secret'):
        missing_keys.append('RAZORPAY_KEY_SECRET')
    
    if missing_keys:
        raise ImproperlyConfigured(
            f'Production requires: {", ".join(missing_keys)}. '
            'Set these in environment variables or .env file.'
        )

# WhatsApp Configuration
WHATSAPP_NUMBER = os.getenv('WHATSAPP_NUMBER', '919037626684')
WHATSAPP_DEFAULT_MESSAGE = os.getenv('WHATSAPP_DEFAULT_MESSAGE', 'Hi, I am interested in your products. Please share more details.')

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # 🔒 SECURITY FIX: Enforce HTTPS in production (set to True by default)
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # 🔒 SECURITY FIX: Additional security headers
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    PERMISSIONS_POLICY = {
        'geolocation': '()',
        'microphone': '()',
        'camera': '()',
    }
else:
    SECURE_SSL_REDIRECT = False

# ===================================================================
# CACHING CONFIGURATION
# ===================================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'syafra-cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}
