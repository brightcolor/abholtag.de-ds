import time

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.addresses.models import AddressKey
from apps.analytics.services import record_event
from apps.core.http import session_hash
from apps.core.ratelimit import is_rate_limited
from apps.notifications.services import notify_admins
from apps.waste_types.models import WasteType

from .forms import CommunityContributionForm, ErrorReportForm
from .models import CorrectionProposal, ErrorReport, ProposalStatus, ProposalVote


def report_form(request):
    address_key = None
    public_id = request.GET.get("adresse") or request.POST.get("adresse")
    if public_id:
        address_key = AddressKey.objects.filter(public_id=public_id).first()
    waste_type = None
    waste_slug = request.GET.get("abfallart") or request.POST.get("abfallart")
    if waste_slug:
        waste_type = WasteType.objects.filter(slug=waste_slug).first()

    if request.method == "POST":
        if is_rate_limited(request, "report"):
            return HttpResponse("Zu viele Meldungen. Bitte versuchen Sie es später erneut.", status=429)
        form = ErrorReportForm(request.POST)
        if form.is_valid():
            report: ErrorReport = form.save(commit=False)
            report.address_key = address_key
            report.street = address_key.street if address_key else None
            report.waste_type = waste_type
            report.session_hash = session_hash(request)
            report.save()
            record_event(
                request, "error_report_submitted",
                address_key=address_key, waste_type=waste_type, status=report.category,
            )
            notify_admins(
                f"Neue Fehlermeldung {report.public_token}",
                f"Kategorie: {report.get_category_display()}\n"
                f"Adresse: {address_key.full_label if address_key else '–'}\n\n{report.description}",
            )
            return redirect("report_status", token=report.public_token)
    else:
        record_event(request, "error_report_opened", address_key=address_key, waste_type=waste_type)
        form = ErrorReportForm(initial={"form_started": time.time()})

    form.fields["form_started"].initial = time.time()
    return render(
        request,
        "community/report_form.html",
        {"form": form, "address_key": address_key, "waste_type": waste_type},
    )


def report_status(request, token):
    report = get_object_or_404(ErrorReport, public_token=token)
    return render(request, "community/report_status.html", {"report": report})


def confirm_proposal(request, pk):
    """Public confirmation of a proposal (quorum building, §22)."""
    if request.method != "POST":
        return redirect("home")
    if is_rate_limited(request, "vote"):
        return HttpResponse("Zu viele Bestätigungen. Bitte später erneut versuchen.", status=429)
    proposal = get_object_or_404(
        CorrectionProposal,
        pk=pk,
        status__in=[ProposalStatus.SUBMITTED, ProposalStatus.AWAITING_CONFIRMATION],
    )
    _, created = ProposalVote.objects.get_or_create(
        proposal=proposal,
        session_hash=session_hash(request),
        defaults={
            "user": request.user if request.user.is_authenticated else None,
            "is_support": request.POST.get("gegenstimme") != "1",
        },
    )
    if created:
        supports = proposal.votes.filter(is_support=True).count()
        objections = proposal.votes.filter(is_support=False).count()
        CorrectionProposal.objects.filter(pk=proposal.pk).update(
            confirmations=supports, objections=objections,
            status=ProposalStatus.AWAITING_CONFIRMATION,
        )
        record_event(request, "proposal_confirmed")
    return render(request, "community/vote_done.html", {"proposal": proposal, "counted": created})


def community_entry(request):
    """Structured community capture – only available in fallback mode (§24)."""
    if not settings.COMMUNITY_MODE_ENABLED:
        return render(request, "community/community_disabled.html", status=404)

    if request.method == "POST":
        if is_rate_limited(request, "report"):
            return HttpResponse("Zu viele Einträge. Bitte später erneut versuchen.", status=429)
        form = CommunityContributionForm(request.POST, request.FILES)
        if form.is_valid():
            contribution = form.save(commit=False)
            contribution.session_hash = session_hash(request)
            contribution.save()
            record_event(request, "community_entry_submitted", waste_type=contribution.waste_type)
            return render(request, "community/community_done.html", {"contribution": contribution})
    else:
        form = CommunityContributionForm(initial={"form_started": time.time()})
    form.fields["form_started"].initial = time.time()
    return render(request, "community/community_form.html", {"form": form})
