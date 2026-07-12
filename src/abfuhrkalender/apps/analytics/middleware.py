"""Analytics middleware - privacy-friendly event tracking."""
import time
import hashlib
import secrets
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class AnalyticsMiddleware(MiddlewareMixin):
    """Captures page views and basic analytics data."""

    SALT = secrets.token_hex(8)  # Rotating salt for session hashing

    def process_request(self, request):
        if not getattr(settings, "ANALYTICS_ENABLED", True):
            return None

        # Skip admin and static paths
        path = request.path_info
        if path.startswith("/admin/") or path.startswith("/static/") or path.startswith("/health/"):
            return None

        # Create a privacy-friendly session identifier
        if not request.session.get("analytics_session_id"):
            request.session["analytics_session_id"] = secrets.token_hex(16)
            request.session.set_expiry(86400 * 30)  # 30 days

        # Store analytics context on request for use in views
        request.analytics = {
            "session_hash": hashlib.sha256(
                (request.session["analytics_session_id"] + self.SALT).encode()
            ).hexdigest(),
            "device_class": self._detect_device(request),
            "browser_family": request.META.get("HTTP_USER_AGENT", "")[:50],
            "referrer_host": self._extract_host(request.META.get("HTTP_REFERER", "")),
        }

    def _detect_device(self, request):
        ua = request.META.get("HTTP_USER_AGENT", "").lower()
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            return "mobile"
        if "tablet" in ua or "ipad" in ua:
            return "tablet"
        return "desktop"

    def _extract_host(self, referer):
        if not referer:
            return ""
        try:
            from urllib.parse import urlparse
            return urlparse(referer).hostname or ""
        except Exception:
            return ""