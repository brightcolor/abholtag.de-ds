from django.urls import path

from . import views

urlpatterns = [
    path("suche/vorschlaege/", views.street_suggestions, name="street_suggestions"),
    path("suche/hausnummern/", views.house_number_list, name="house_number_list"),
]
