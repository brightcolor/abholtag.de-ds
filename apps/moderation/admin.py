from django.contrib import admin

from .models import ModerationComment


@admin.register(ModerationComment)
class ModerationCommentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "author", "is_public", "created_at")
    list_filter = ("is_public",)
