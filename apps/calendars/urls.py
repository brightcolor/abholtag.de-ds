from django.urls import path

from . import views

urlpatterns = [
    path("calendar/address/<str:public_id>/<slug:waste_slug>.ics", views.address_feed, name="address_feed"),
    path("a/<str:public_id>/kalender/", views.subscribe_page, name="subscribe_page"),
]
