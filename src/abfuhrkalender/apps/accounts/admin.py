"""Admin for accounts."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "display_name", "role", "trust_level", "is_active"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "display_name"]
    ordering = ["email"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Persönliche Daten", {"fields": ["display_name", "role"]}),
        ("Vertrauensniveau", {"fields": ["trust_level", "accepted_contributions", "rejected_contributions"]}),
        ("Berechtigungen", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Zwei-Faktor", {"fields": ["is_two_factor_enabled"]}),
        ("Wichtige Daten", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (None, {
            "classes": ["wide"],
            "fields": ["email", "display_name", "password1", "password2", "role"],
        }),
    ]