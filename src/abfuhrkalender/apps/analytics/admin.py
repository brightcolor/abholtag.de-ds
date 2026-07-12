"""Admin for analytics."""
from django.contrib import admin
from .models import AnalyticsEvent, AnalyticsAggregate

@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "timestamp", "session_hash", "device_class"]
    list_filter = ["event_type", "device_class"]
    readonly_fields = ["timestamp"]

@admin.register(AnalyticsAggregate)
class AnalyticsAggregateAdmin(admin.ModelAdmin):
    list_display = ["period", "period_start", "event_type", "count"]
    list_filter = ["period", "event_type"]