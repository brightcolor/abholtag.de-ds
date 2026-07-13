"""SEO plumbing: sitemaps, robots.txt, IndexNow key."""

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.http import Http404, HttpResponse

from apps.addresses.models import AssignmentStatus, Street


def _site_protocol():
    return "https" if settings.SITE_BASE_URL.startswith("https") else "http"


class StaticSitemap(Sitemap):
    protocol = property(lambda self: _site_protocol())
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return ["/", "/strassen/", "/status/", "/datenschutz/", "/impressum/"]

    def location(self, item):
        return item


class StreetSitemap(Sitemap):
    protocol = property(lambda self: _site_protocol())
    priority = 0.6
    changefreq = "weekly"
    limit = 5000

    def items(self):
        return (
            Street.objects.filter(is_active=True, assignments__status=AssignmentStatus.ACTIVE)
            .exclude(slug__isnull=True)
            .distinct()
            .order_by("pk")
        )

    def location(self, obj):
        return f"/strasse/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {"static": StaticSitemap, "strassen": StreetSitemap}


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /intern/",
        "Disallow: /a/",  # personalisierte Adress-Seiten
        "Disallow: /melden/",
        "Disallow: /suche/",
        "Disallow: /api/",
        "Allow: /",
        "",
        f"Sitemap: {settings.SITE_BASE_URL.rstrip('/')}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def indexnow_key(request, key):
    """Serves the IndexNow key file (https://www.indexnow.org/)."""
    configured = getattr(settings, "INDEXNOW_KEY", "")
    if not configured or key != configured:
        raise Http404
    return HttpResponse(configured, content_type="text/plain; charset=utf-8")
