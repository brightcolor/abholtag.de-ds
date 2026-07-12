from django.conf import settings


class SecurityHeadersMiddleware:
    """Adds CSP, Permissions-Policy and related headers (§34)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # The Django admin (Jazzmin) relies on inline scripts/styles as well,
        # so a single relaxed-inline policy is used consistently.
        response.headers.setdefault("Content-Security-Policy", settings.CSP_POLICY)
        response.headers.setdefault("Permissions-Policy", settings.PERMISSIONS_POLICY)
        return response
