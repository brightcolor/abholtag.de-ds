from django.urls import path
from . import views

app_name = "community"
urlpatterns = [
    path("new/", views.ErrorReportView.as_view(), name="error_report"),
    path("<slug:public_id>/", views.ReportStatusView.as_view(), name="report_status"),
    path("correction/new/", views.CorrectionView.as_view(), name="correction"),
]