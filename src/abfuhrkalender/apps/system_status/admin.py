"""Admin for system status."""
from django.contrib import admin
from .models import SystemCheck

@admin.register(SystemCheck)
class SystemCheckAdmin(admin.ModelAdmin):
    list_display = ["check_name", "status", "checked_at", "duration_ms"]
    list_filter = ["status", "check_name"]