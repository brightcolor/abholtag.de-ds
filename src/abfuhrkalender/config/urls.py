from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    
    # Health checks
    path("health/", include("apps.system_status.status_urls")),
    
    # Public views
    path("", include("apps.core.urls")),
    path("address/", include("apps.addresses.urls")),
    path("calendar/", include("apps.calendars.urls")),
    
    # Community
    path("report/", include("apps.community.urls")),
    path("moderation/", include("apps.moderation.urls")),
    
    # Accounts
    path("accounts/", include("apps.accounts.urls")),
    
    # API
    path("api/v1/", include("apps.public_api.urls")),
    
    # Analytics (admin only)
    path("analytics/", include("apps.analytics.urls")),
    
    # System status
    path("status/", include("apps.system_status.status_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)