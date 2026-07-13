from django.urls import path

from . import seo_views, views

urlpatterns = [
    path("", views.home, name="home"),
    path("strassen/", seo_views.street_index, name="street_index"),
    path("strasse/<slug:slug>/", seo_views.street_page, name="street_page"),
    path("termine/", views.resolve, name="resolve"),
    path("a/<str:public_id>/", views.address_schedule, name="address_schedule"),
    path("a/<str:public_id>/druck/", views.address_schedule_print, name="address_schedule_print"),
]
