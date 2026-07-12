"""Community views - error reports, corrections."""
from django.views.generic import TemplateView, DetailView, CreateView
from .models import ErrorReport, CorrectionProposal


class ErrorReportView(CreateView):
    model = ErrorReport
    template_name = "community/error_report.html"
    fields = ["category", "description", "suggested_correction", "source_info", "reporter_email", "affected_street"]


class ReportStatusView(DetailView):
    model = ErrorReport
    template_name = "community/report_status.html"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"


class CorrectionView(CreateView):
    model = CorrectionProposal
    template_name = "community/correction.html"
    fields = ["target_type", "reason", "new_value", "source", "confidence"]
