from django.urls import path

from . import views

urlpatterns = [
    path("suche/vorschlaege/", views.street_suggestions, name="street_suggestions"),
]
