from django.urls import path

from . import views

urlpatterns = [
    path("", views.report_form, name="report_form"),
    path("status/<str:token>/", views.report_status, name="report_status"),
    path("vorschlag/<int:pk>/bestaetigen/", views.confirm_proposal, name="confirm_proposal"),
    path("community/", views.community_entry, name="community_entry"),
]
