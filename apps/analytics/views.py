import csv
import json
from datetime import date, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render

from .models import AnalyticsEvent, EventType


def _parse_range(request) -> tuple[date, date]:
    try:
        days = int(request.GET.get("zeitraum", "30"))
    except ValueError:
        days = 30
    days = max(1, min(days, 365))
    end = date.today()
    return end - timedelta(days=days - 1), end


@staff_member_required
def dashboard(request):
    """AdminLTE analytics dashboard (§18) – internal only (§17)."""
    start, end = _parse_range(request)
    events = AnalyticsEvent.objects.filter(created_at__date__gte=start, created_at__date__lte=end)

    event_filter = request.GET.get("ereignis", "")
    if event_filter:
        events = events.filter(event_type=event_filter)
    device_filter = request.GET.get("geraet", "")
    if device_filter:
        events = events.filter(device_class=device_filter)

    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    base = AnalyticsEvent.objects

    def count(event_type, since):
        return base.filter(event_type=event_type, created_at__date__gte=since).count()

    from apps.community.models import CommunityContribution, CorrectionProposal, ErrorReport

    cards = {
        "views_today": count(EventType.PAGE_VIEW, today),
        "views_week": count(EventType.PAGE_VIEW, week_ago),
        "views_month": count(EventType.PAGE_VIEW, month_ago),
        "resolved_month": count(EventType.ADDRESS_RESOLVED, month_ago),
        "no_result_month": count(EventType.STREET_SEARCH_NO_RESULT, month_ago),
        "feed_month": count(EventType.CALENDAR_FEED_REQUESTED, month_ago),
        "active_subscriptions": estimate_active_subscriptions(),
        "open_reports": ErrorReport.objects.filter(status__in=["new", "in_review"]).count(),
        "open_proposals": CorrectionProposal.objects.filter(
            status__in=["submitted", "awaiting_confirmation", "under_review"]
        ).count(),
        "open_contributions": CommunityContribution.objects.filter(status="submitted").count(),
    }

    # time series for the chart (all requested events per day)
    per_day = {
        str(row["created_at__date"]): row["n"]
        for row in events.values("created_at__date").annotate(n=Count("id"))
    }
    series_labels, series_values = [], []
    cursor = start
    while cursor <= end:
        series_labels.append(cursor.strftime("%d.%m."))
        series_values.append(per_day.get(str(cursor), 0))
        cursor += timedelta(days=1)

    def top(queryset, field, limit=10):
        rows = (
            queryset.exclude(**{f"{field}__isnull": True})
            .values(field)
            .annotate(n=Count("id"))
            .order_by("-n")[:limit]
        )
        return rows

    top_districts = (
        events.exclude(district__isnull=True)
        .values("district__name")
        .annotate(n=Count("id"))
        .order_by("-n")[:10]
    )
    top_streets = (
        events.exclude(street__isnull=True)
        .values("street__name")
        .annotate(n=Count("id"))
        .order_by("-n")[:10]
    )
    top_no_result = (
        events.filter(event_type=EventType.STREET_SEARCH_NO_RESULT)
        .exclude(query="")
        .values("query")
        .annotate(n=Count("id"))
        .order_by("-n")[:10]
    )
    clients = (
        events.filter(event_type=EventType.CALENDAR_FEED_REQUESTED)
        .exclude(calendar_client="")
        .values("calendar_client")
        .annotate(n=Count("id"))
        .order_by("-n")[:10]
    )
    per_type = events.values("event_type").annotate(n=Count("id")).order_by("-n")

    from django.contrib import admin as django_admin

    return render(
        request,
        "analytics/dashboard.html",
        {
            **django_admin.site.each_context(request),
            "cards": cards,
            "start": start,
            "end": end,
            "event_types": EventType.choices,
            "event_filter": event_filter,
            "device_filter": device_filter,
            "series_labels": json.dumps(series_labels),
            "series_values": json.dumps(series_values),
            "top_districts": top_districts,
            "top_streets": top_streets,
            "top_no_result": top_no_result,
            "clients": clients,
            "per_type": per_type,
            "title": "Nutzungsstatistik",
        },
    )


def estimate_active_subscriptions() -> int:
    """Estimated active calendar subscriptions (§19, documented method):

    Distinct (address_key, calendar_client) pairs that requested the feed on
    at least two different days within the last 21 days. One-off downloads
    do not recur and are therefore excluded by design.
    """
    since = date.today() - timedelta(days=21)
    rows = (
        AnalyticsEvent.objects.filter(
            event_type=EventType.CALENDAR_FEED_REQUESTED,
            created_at__date__gte=since,
            address_key__isnull=False,
        )
        .values("address_key_id", "calendar_client")
        .annotate(days=Count("created_at__date", distinct=True))
        .filter(days__gte=2)
    )
    return rows.count()


@staff_member_required
def export_csv(request):
    start, end = _parse_range(request)
    rows = (
        AnalyticsEvent.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
        .values("created_at__date", "event_type")
        .annotate(n=Count("id"))
        .order_by("created_at__date")
    )
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="statistik.csv"'
    writer = csv.writer(response)
    writer.writerow(["Datum", "Ereignis", "Anzahl"])
    for row in rows:
        writer.writerow([row["created_at__date"], row["event_type"], row["n"]])
    return response
