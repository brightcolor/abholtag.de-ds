from django.urls import path
from . import views

app_name = "system_status"
urlpatterns = [
    path("", views.HealthView.as_view(), name="health"),
    path("live/", views.LivenessView.as_view(), name="liveness"),
    path("ready/", views.ReadinessView.as_view(), name="readiness"),
    path("dashboard/", views.SystemStatusDashboardView.as_view(), name="dashboard"),
]