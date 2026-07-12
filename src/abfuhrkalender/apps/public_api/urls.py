from django.urls import path
from . import views

app_name = "api"
urlpatterns = [
    path("waste-types/", views.WasteTypeListAPI.as_view(), name="waste_types"),
    path("streets/", views.StreetSearchAPI.as_view(), name="streets"),
    path("address/resolve/", views.AddressResolveAPI.as_view(), name="address_resolve"),
    path("addresses/<uuid:public_id>/collections/", views.AddressCollectionsAPI.as_view(), name="address_collections"),
    path("zones/<str:letter>/collections/", views.ZoneCollectionsAPI.as_view(), name="zone_collections"),
    path("reports/", views.CreateReportAPI.as_view(), name="create_report"),
    path("corrections/", views.CreateCorrectionAPI.as_view(), name="create_correction"),
]