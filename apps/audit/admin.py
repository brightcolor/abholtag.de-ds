from django.contrib import admin

from .models import AuditLog, ChangeSet


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "model_label", "object_repr", "action", "actor", "reason")
    list_filter = ("action", "model_label")
    search_fields = ("object_repr", "object_pk", "reason")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChangeSet)
class ChangeSetAdmin(admin.ModelAdmin):
    list_display = ("id", "actor", "reason", "created_at")
