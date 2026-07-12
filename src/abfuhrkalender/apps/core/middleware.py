"""Theme middleware - persists dark/light mode preference."""
from django.utils.deprecation import MiddlewareMixin


class ThemeMiddleware(MiddlewareMixin):
    """Reads theme preference from cookie and attaches to request."""

    def process_request(self, request):
        theme = request.COOKIES.get("akl_theme", "system")
        if theme not in ("light", "dark", "system"):
            theme = "system"
        request.theme = theme
        request.session["theme"] = theme