"""Analytics dashboard and data export."""
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from .models import AnalyticsEvent, AnalyticsAggregate
from django.db.models import Count


@method_decorator(staff_member_required, name="dispatch")
class AnalyticsDashboardView(TemplateView):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["today_count"] = AnalyticsEvent.objects.filter(
            timestamp__date="2026-07-12"
        ).count()
        context["recent_events"] = AnalyticsEvent.objects.order_by("-timestamp")[:50]
        return context


@method_decorator(staff_member_required, name="dispatch")
class AnalyticsDataView(View):
    def get(self, request, period, *args, **kwargs):
        aggregates = AnalyticsAggregate.objects.filter(period=period).order_by("-period_start")[:90]
        data = [
            {"period_start": a.period_start.isoformat(), "event_type": a.event_type, "count": a.count}
            for a in aggregates
        ]
        return JsonResponse(data, safe=False)
