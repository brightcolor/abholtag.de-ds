from django.conf import settings


def site_settings(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "SITE_BASE_URL": settings.SITE_BASE_URL,
        "OPERATOR_NAME": settings.OPERATOR_NAME,
        "OPERATOR_ADDRESS": settings.OPERATOR_ADDRESS,
        "OPERATOR_EMAIL": settings.OPERATOR_EMAIL,
        "COMMUNITY_MODE_ENABLED": settings.COMMUNITY_MODE_ENABLED,
    }
