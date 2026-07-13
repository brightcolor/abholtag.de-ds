from django.contrib import admin

from apps.schedules.admin import status_badge

from .models import ImportRun


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ("id", "parser_key", "kind", status_badge, "started_at", "finished_at", "issue_count")
    list_filter = ("status", "kind", "parser_key")
    readonly_fields = ("started_at", "finished_at", "stats", "issues", "diff", "log")

    @admin.display(description="Hinweise")
    def issue_count(self, obj):
        return len(obj.issues or [])
