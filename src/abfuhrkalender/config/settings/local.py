from .base import *  # noqa: F403, F401

DEBUG = True

ALLOWED_HOSTS = ["*"]

# SQLite for local dev without Docker
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR.parent / "db.sqlite3",
    }
}

# Disable CSP in dev
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ("'self'", "'unsafe-inline'", "*"),
        "style-src": ("'self'", "'unsafe-inline'", "*"),
        "script-src": ("'self'", "'unsafe-inline'", "*"),
        "img-src": ("'self'", "data:", "blob:", "*"),
    },
}

# Enable debug toolbar in dev
INSTALLED_APPS += ["django_extensions"]

# Less strict password validation in dev
AUTH_PASSWORD_VALIDATORS = []

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}