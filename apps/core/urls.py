from django.urls import path

from . import views

urlpatterns = [
    path("impressum/", views.imprint, name="imprint"),
    path("datenschutz/", views.privacy, name="privacy"),
    path("api/", views.api_docs, name="api_docs"),
]
