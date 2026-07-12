from django.urls import path
from . import views

app_name = "analytics"
urlpatterns = [
    path("dashboard/", views.AnalyticsDashboardView.as_view(), name="dashboard"),
    path("data/<str:period>/", views.AnalyticsDataView.as_view(), name="data"),
]