from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, UserTrustProfile


@admin.register(User)
class ProjectUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_staff", "is_active", "last_login")


@admin.register(UserTrustProfile)
class UserTrustProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "score", "accepted_count", "rejected_count", "last_contribution_at")
    search_fields = ("user__username",)
