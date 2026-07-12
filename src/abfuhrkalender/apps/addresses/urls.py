from django.urls import path
from . import views

app_name = "addresses"
urlpatterns = [
    path("search/", views.StreetSearchView.as_view(), name="search_streets"),
    path("resolve/", views.AddressResolveView.as_view(), name="resolve"),
]