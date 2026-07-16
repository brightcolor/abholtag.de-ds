from django.urls import path

from . import views

urlpatterns = [
    path("impressum/", views.imprint, name="imprint"),
    path("datenschutz/", views.privacy, name="privacy"),
    path("datenquelle/", views.data_provenance, name="data_provenance"),
    path("api/", views.api_docs, name="api_docs"),
]
