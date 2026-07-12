from django.urls import path

from . import views

urlpatterns = [
    path("", views.admin_status, name="admin_status"),
]
