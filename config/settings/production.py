from .base import *  # noqa
from .base import env

EMAIL_CONFIG = env.email_url("DJANGO_EMAIL_URL")
vars().update(EMAIL_CONFIG)
SERVER_EMAIL = EMAIL_CONFIG["EMAIL_HOST_USER"]
EMAIL_TIMEOUT = 5

SECRET_KEY = env.str("DJANGO_SECRET_KEY")
ADMIN_URL = env.str("DJANGO_ADMIN_URL")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
OPENAI_KEY = env.str("DJANGO_OPENAI")
GEMINIAPI_KEY = env.str("DJANGO_GEMINIAPI")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env.str("DATABASE_NAME"),
        'USER': env.str("DATABASE_USER_SNAME"),
        'PASSWORD': env.str("DATABASE_PASS_WORD"),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}



SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)

SECURE_SSL_HOST = True
SECURE_BROWSER_XSS_FILTER = True

INSTALLED_APPS += [
    # "django_extensions",
]

log_filename = str(BASE_DIR("logs", "bizanalytic.log"))
os.makedirs(os.path.dirname(log_filename), exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse",},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue",},
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "rotating_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(BASE_DIR("logs", "bizanalytic.log")),
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "mail_admins", "rotating_file"],
            "level": "INFO",
        },
    },
}

RECAPTCHA_PUBLIC_KEY = env.str("DJANGO_RECAPTCHA_PUBLIC", None)
RECAPTCHA_PRIVATE_KEY = env.str("DJANGO_RECAPTCHA_PRIVATE", None)

UPLOADDOCUMENTKEY = env.str("UPLOAD_DOCUMENT_KEY")