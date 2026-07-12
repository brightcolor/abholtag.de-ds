from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("termine/", views.resolve, name="resolve"),
    path("a/<str:public_id>/", views.address_schedule, name="address_schedule"),
    path("a/<str:public_id>/druck/", views.address_schedule_print, name="address_schedule_print"),
]
