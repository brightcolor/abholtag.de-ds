"""Admin for audit."""
from django.contrib import admin
from .models import ChangeSet, AuditLog

@admin.register(ChangeSet)
class ChangeSetAdmin(admin.ModelAdmin):
    list_display = ["action", "user", "timestamp", "source"]
    list_filter = ["action", "source"]

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["model_name", "object_repr", "field_name", "change_set"]
    list_filter = ["model_name"]