"""Base settings shared by all environments."""

from pathlib import Path

from config.env import env, env_bool, env_int, env_list

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", [])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django_otp",
    "django_otp.plugins.otp_totp",
    # project apps
    "apps.core",
    "apps.accounts",
    "apps.waste_types",
    "apps.addresses",
    "apps.schedules",
    "apps.data_sources",
    "apps.imports",
    "apps.calendars",
    "apps.analytics",
    "apps.reports",
    "apps.community",
    "apps.moderation",
    "apps.notifications",
    "apps.audit",
    "apps.public_api",
    "apps.system_status",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

if env("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "abfuhrkalender"),
            "USER": env("POSTGRES_USER", "abfuhrkalender"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST": env("POSTGRES_HOST", "db"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"

# ---------------------------------------------------------------------------
# I18N
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / media
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))

# ---------------------------------------------------------------------------
# Security defaults (hardened further in prod.py)
# ---------------------------------------------------------------------------

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Content-Security-Policy applied by apps.core.middleware.SecurityHeadersMiddleware
CSP_POLICY = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=()"

# Enforce TOTP two-factor auth for /admin (recommended in production)
ADMIN_OTP_REQUIRED = env_bool("ADMIN_OTP_REQUIRED", False)

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "abfuhrkalender@example.org")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ADMINS = [("Admin", email) for email in env_list("ADMIN_EMAILS", [])]

# ---------------------------------------------------------------------------
# Caching (used for rate limiting and feed caching; use Redis in production
# via CACHE_URL if multiple workers are deployed)
# ---------------------------------------------------------------------------

if env("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": env("REDIS_URL"),
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "abfuhrkalender",
        }
    }

# ---------------------------------------------------------------------------
# Project settings
# ---------------------------------------------------------------------------

SITE_NAME = env("SITE_NAME", "Abfuhrkalender Lübeck")
SITE_TAGLINE = env("SITE_TAGLINE", "Abfuhrtermine für die Hansestadt Lübeck – einfach, aktuell, abonnierbar.")
SITE_BASE_URL = env("SITE_BASE_URL", "http://localhost:8000")
OPERATOR_NAME = env("OPERATOR_NAME", "")
OPERATOR_ADDRESS = env("OPERATOR_ADDRESS", "")
OPERATOR_EMAIL = env("OPERATOR_EMAIL", "")

# SEO: Search-Console-Verifizierung (Meta-Tag) und IndexNow-Schlüssel
GOOGLE_SITE_VERIFICATION = env("GOOGLE_SITE_VERIFICATION", "")
INDEXNOW_KEY = env("INDEXNOW_KEY", "")

# Analytics privacy configuration
ANALYTICS_ENABLED = env_bool("ANALYTICS_ENABLED", True)
ANALYTICS_RAW_RETENTION_DAYS = env_int("ANALYTICS_RAW_RETENTION_DAYS", 90)
ANALYTICS_SESSION_SALT_ROTATION = "daily"  # documented in docs/ANALYTICS-DATENSCHUTZ.md

# Community / quorum feature flags (§22 – disabled by default)
COMMUNITY_MODE_ENABLED = env_bool("COMMUNITY_MODE_ENABLED", False)
COMMUNITY_AUTO_PUBLISH = env_bool("COMMUNITY_AUTO_PUBLISH", False)

# Rate limits (requests per window seconds)
RATE_LIMITS = {
    "search": (env_int("RATE_LIMIT_SEARCH", 60), 60),
    "api": (env_int("RATE_LIMIT_API", 120), 60),
    "report": (env_int("RATE_LIMIT_REPORT", 5), 600),
    "vote": (env_int("RATE_LIMIT_VOTE", 10), 600),
}

# Minimum seconds a report form must be open before submission (bot protection)
FORM_MIN_SECONDS = env_int("FORM_MIN_SECONDS", 3)

# ---------------------------------------------------------------------------
# Jazzmin (AdminLTE based admin)
# ---------------------------------------------------------------------------

JAZZMIN_SETTINGS = {
    "site_title": "Abfuhrkalender Lübeck",
    "site_header": "Abfuhrkalender Lübeck",
    "site_brand": "Abfuhrkalender",
    "welcome_sign": "Verwaltung des Abfuhrkalenders Lübeck",
    "copyright": "Abfuhrkalender Lübeck (Open Source)",
    "search_model": ["addresses.Street"],
    "icons": {
        "auth.Group": "fas fa-users",
        "accounts.User": "fas fa-user",
        "accounts.UserTrustProfile": "fas fa-user-shield",
        "waste_types.WasteType": "fas fa-recycle",
        "addresses.Street": "fas fa-road",
        "addresses.StreetAlias": "fas fa-signature",
        "addresses.StreetAssignment": "fas fa-map-signs",
        "addresses.District": "fas fa-map",
        "addresses.City": "fas fa-city",
        "addresses.AddressKey": "fas fa-home",
        "schedules.CollectionZone": "fas fa-route",
        "schedules.ScheduleYear": "fas fa-calendar-alt",
        "schedules.CollectionDate": "fas fa-calendar-day",
        "data_sources.DataSource": "fas fa-plug",
        "data_sources.SourceDocument": "fas fa-file-pdf",
        "imports.ImportRun": "fas fa-file-import",
        "community.ErrorReport": "fas fa-bug",
        "community.CorrectionProposal": "fas fa-edit",
        "community.ProposalVote": "fas fa-vote-yea",
        "community.QuorumRule": "fas fa-balance-scale",
        "community.CommunityContribution": "fas fa-hands-helping",
        "moderation.ModerationComment": "fas fa-comments",
        "audit.AuditLog": "fas fa-clipboard-list",
        "audit.ChangeSet": "fas fa-layer-group",
        "analytics.AnalyticsEvent": "fas fa-chart-line",
        "analytics.AnalyticsAggregate": "fas fa-chart-bar",
    },
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Statistiken", "url": "/intern/statistik/", "permissions": ["analytics.view_analyticsevent"]},
        {"name": "Moderation", "url": "/intern/moderation/", "permissions": ["community.view_errorreport"]},
        {"name": "Systemstatus", "url": "/intern/status/", "permissions": ["auth.view_user"]},
        {"name": "Öffentliche Seite", "url": "/", "new_window": True},
    ],
    "usermenu_links": [
        {"name": "Öffentliche Seite", "url": "/", "new_window": True},
    ],
    "order_with_respect_to": [
        "schedules",
        "schedules.scheduleyear",
        "schedules.collectiondate",
        "schedules.collectionzone",
        "addresses",
        "addresses.street",
        "addresses.streetassignment",
        "addresses.housenumber",
        "waste_types",
        "imports",
        "data_sources",
        "community",
        "moderation",
        "analytics",
        "audit",
        "accounts",
        "auth",
    ],
    # Rohdaten- und Zwischentabellen aus der Seitenleiste heraushalten –
    # erreichbar bleiben sie über Dashboard, Statistik und Direktlinks.
    "hide_models": [
        "analytics.analyticsevent",
        "analytics.analyticsaggregate",
        "addresses.addresskey",
        "addresses.streetalias",
        "addresses.city",
        "community.proposalvote",
        "moderation.moderationcomment",
        "audit.changeset",
        "accounts.usertrustprofile",
        "otp_totp.totpdevice",
    ],
    "site_logo": "favicon.svg",
    "site_logo_classes": "ak-admin-logo",
    "login_logo": "favicon.svg",
    "related_modal_active": True,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "schedules.collectiondate": "single",
        "waste_types.wastetype": "collapsible",
    },
    "custom_css": "css/admin-custom.css",
    "show_ui_builder": False,
}

# Bewusst KEIN dark_mode_theme: die Mischung aus dunklen Bootswatch-Karten
# und hellem Layout erzeugte unlesbare Kontraste. Der Admin ist durchgängig
# hell; die Markenfarben kommen aus admin-custom.css.
JAZZMIN_UI_TWEAKS = {
    "theme": "flatly",
    "navbar": "navbar-white navbar-light",
    "sidebar": "sidebar-dark-primary",
    "brand_colour": False,
    "accent": "accent-teal",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "apps": {"level": env("LOG_LEVEL", "INFO")},
    },
}
