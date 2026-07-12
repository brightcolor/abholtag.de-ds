from django.contrib import admin

from .models import AnalyticsAggregate, AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "created_at", "street", "district", "device_class", "calendar_client", "status")
    list_filter = ("event_type", "device_class", "browser_family", "calendar_client")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in AnalyticsEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AnalyticsAggregate)
class AnalyticsAggregateAdmin(admin.ModelAdmin):
    list_display = ("date", "event_type", "dimension", "count")
    list_filter = ("event_type",)
    date_hierarchy = "date"
    search_fields = ("dimension",)
