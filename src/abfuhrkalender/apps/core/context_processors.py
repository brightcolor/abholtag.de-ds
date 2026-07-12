"""Context processors for global template variables."""
from django.conf import settings


def theme(request):
    """Expose theme preference to templates."""
    return {"theme": getattr(request, "theme", "system")}


def site_settings(_request):
    """Expose site-wide settings."""
    return {
        "SITE_NAME": "Abfuhrkalender Lübeck",
        "SITE_DESCRIPTION": "Abfuhrtermine für die Hansestadt Lübeck",
        "ANALYTICS_ENABLED": settings.ANALYTICS_ENABLED,
    }