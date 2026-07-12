"""Moderation queue and review interface."""
from django.views.generic import TemplateView, DetailView
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from ..community.models import ErrorReport, CorrectionProposal


@method_decorator(staff_member_required, name="dispatch")
class ModerationQueueView(TemplateView):
    template_name = "moderation/queue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reports"] = ErrorReport.objects.filter(status="new").order_by("-created_at")[:20]
        context["proposals"] = CorrectionProposal.objects.filter(status="new").order_by("-created_at")[:20]
        return context


@method_decorator(staff_member_required, name="dispatch")
class ReportDetailView(DetailView):
    model = ErrorReport
    template_name = "moderation/report_detail.html"


@method_decorator(staff_member_required, name="dispatch")
class ProposalDetailView(DetailView):
    model = CorrectionProposal
    template_name = "moderation/proposal_detail.html"
