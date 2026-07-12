from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("health/live", views.health_live, name="health_live"),
    path("health/ready", views.health_ready, name="health_ready"),
    path("status/", views.public_status, name="public_status"),
]
