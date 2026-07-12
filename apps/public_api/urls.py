from django.urls import path

from . import views

urlpatterns = [
    path("waste-types", views.waste_types, name="api_waste_types"),
    path("streets", views.streets, name="api_streets"),
    path("address/resolve", views.resolve, name="api_resolve"),
    path("addresses/<str:public_id>/collections", views.collections, name="api_collections"),
    path("zones/<str:code>/collections", views.zone_collections, name="api_zone_collections"),
    path("reports", views.create_report, name="api_create_report"),
    path("corrections", views.create_correction, name="api_create_correction"),
    path("proposals/<int:pk>/confirm", views.confirm_proposal, name="api_confirm_proposal"),
    path("openapi.json", views.openapi_spec, name="api_openapi"),
]
