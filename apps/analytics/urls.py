from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="analytics_dashboard"),
    path("export.csv", views.export_csv, name="analytics_export"),
]
