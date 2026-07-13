from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.urls import include, path

from apps.core import views as core_views
from apps.core.seo import SITEMAPS, indexnow_key, robots_txt

urlpatterns = [
    path("", include("apps.core.urls")),
    path("", include("apps.addresses.urls")),
    path("", include("apps.schedules.urls")),
    path("", include("apps.calendars.urls")),
    path("melden/", include("apps.community.urls")),
    path("api/v1/", include("apps.public_api.urls")),
    path("intern/", include("apps.moderation.urls")),
    path("intern/statistik/", include("apps.analytics.urls")),
    path("intern/status/", include("apps.system_status.admin_urls")),
    path("", include("apps.system_status.urls")),
    # Eigene Admin-Startseite (Dashboard) faengt exakt /admin/ ab;
    # alle Detailseiten laufen weiter ueber den Django-Admin darunter.
    path("sitemap.xml", sitemap_view, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", robots_txt, name="robots"),
    path("<str:key>.txt", indexnow_key, name="indexnow_key"),
    path("admin/", core_views.admin_dashboard),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"
handler403 = "apps.core.views.error_403"
