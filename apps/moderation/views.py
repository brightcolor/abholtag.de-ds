from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from apps.community.models import (
    CommunityContribution,
    ContributionStatus,
    CorrectionProposal,
    ErrorReport,
    ProposalStatus,
    ReportStatus,
)
from apps.imports.models import ImportRun, ImportRunStatus
from apps.schedules.models import ScheduleYear, ScheduleYearStatus


@staff_member_required
def queue(request):
    """Moderation queue: everything that needs human attention (§27)."""
    status_filter = request.GET.get("status", "offen")

    reports = ErrorReport.objects.select_related("street", "waste_type")
    proposals = CorrectionProposal.objects.select_related("street", "waste_type")
    contributions = CommunityContribution.objects.select_related("waste_type")

    if status_filter == "offen":
        reports = reports.filter(status__in=[ReportStatus.NEW, ReportStatus.IN_REVIEW])
        proposals = proposals.filter(
            status__in=[
                ProposalStatus.SUBMITTED,
                ProposalStatus.AWAITING_CONFIRMATION,
                ProposalStatus.QUORUM_REACHED,
                ProposalStatus.UNDER_REVIEW,
            ]
        )
        contributions = contributions.filter(status=ContributionStatus.SUBMITTED)

    review_imports = ImportRun.objects.filter(
        status__in=[ImportRunStatus.NEEDS_REVIEW, ImportRunStatus.VALIDATION_FAILED]
    )
    review_years = ScheduleYear.objects.filter(
        status__in=[
            ScheduleYearStatus.PARSED,
            ScheduleYearStatus.NEEDS_REVIEW,
            ScheduleYearStatus.APPROVED,
        ]
    ).select_related("waste_type")

    from django.contrib import admin as django_admin

    return render(
        request,
        "moderation/queue.html",
        {
            **django_admin.site.each_context(request),
            "title": "Moderation",
            "status_filter": status_filter,
            "reports": reports.order_by("-created_at")[:50],
            "proposals": proposals.order_by("-created_at")[:50],
            "contributions": contributions.order_by("-created_at")[:50],
            "review_imports": review_imports[:20],
            "review_years": review_years[:20],
        },
    )
