from django.urls import path
from . import views

app_name = "moderation"
urlpatterns = [
    path("", views.ModerationQueueView.as_view(), name="queue"),
    path("report/<uuid:pk>/", views.ReportDetailView.as_view(), name="report_detail"),
    path("proposal/<uuid:pk>/", views.ProposalDetailView.as_view(), name="proposal_detail"),
]