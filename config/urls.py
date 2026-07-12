from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

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
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"
handler403 = "apps.core.views.error_403"
