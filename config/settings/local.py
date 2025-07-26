from .base import *  # noqa
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]

INSTALLED_APPS += [
    # "debug_toolbar",
    "rosetta",
]

ADMIN_URL = env.str("DJANGO_ADMIN_URL")

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
# MIDDLEWARE += [
#      "debug_toolbar.middleware.DebugToolbarMiddleware",
# ]
INTERNAL_IPS = [
    "127.0.0.1",
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ROSETTA_MESSAGES_PER_PAGE = 100
ROSETTA_ENABLE_TRANSLATION_SUGGESTIONS = True
YANDEX_TRANSLATE_KEY = env.str("DJANGO_YANDEX_TRANSLATE_KEY", None)

ACCOUNT_EMAIL_VERIFICATION = "none"

ADMINS = (
    ("Admin", "admin@gmail.com"),
    ("Owner", "owner@gmail.com"),
)

RECAPTCHA_PUBLIC_KEY = env.str("DJANGO_RECAPTCHA_PUBLIC", None)
RECAPTCHA_PRIVATE_KEY = env.str("DJANGO_RECAPTCHA_PRIVATE", None)