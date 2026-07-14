from django.conf import settings
from django.http import HttpResponse


class SecurityHeadersMiddleware:
    """Adds CSP, Permissions-Policy and related headers (§34).

    The public JSON API is open data, so read access is CORS-enabled for any
    origin (no cookies/credentials involved) – this lets browser apps consume
    it directly.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_api = request.path.startswith("/api/")
        if is_api and request.method == "OPTIONS":
            response = HttpResponse(status=204)  # CORS preflight
        else:
            response = self.get_response(request)
        # The Django admin (Jazzmin) relies on inline scripts/styles as well,
        # so a single relaxed-inline policy is used consistently.
        response.headers.setdefault("Content-Security-Policy", settings.CSP_POLICY)
        response.headers.setdefault("Permissions-Policy", settings.PERMISSIONS_POLICY)
        if is_api:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Max-Age"] = "86400"
        return response
