"""URL patterns for health checks (separate from admin urls)."""
from django.urls import path
from . import views

# No app_name to avoid namespace conflicts
urlpatterns = [
    path("", views.HealthView.as_view(), name="health"),
    path("live/", views.LivenessView.as_view(), name="liveness"),
    path("ready/", views.ReadinessView.as_view(), name="readiness"),
    path("dashboard/", views.SystemStatusDashboardView.as_view(), name="system_status_dashboard"),
]