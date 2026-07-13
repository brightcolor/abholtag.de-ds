from django.contrib import admin

from apps.schedules.admin import status_badge

from .models import (
    CommunityContribution,
    CorrectionProposal,
    ErrorReport,
    ProposalVote,
    QuorumRule,
)


@admin.register(ErrorReport)
class ErrorReportAdmin(admin.ModelAdmin):
    list_display = ("public_token", "category", status_badge, "street", "waste_type", "created_at")
    list_filter = ("status", "category", "waste_type")
    search_fields = ("public_token", "description", "street__name")
    readonly_fields = ("public_token", "session_hash", "created_at", "updated_at")


@admin.register(CorrectionProposal)
class CorrectionProposalAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", status_badge, "street", "confirmations", "objections", "created_at")
    list_filter = ("status", "kind", "waste_type")
    search_fields = ("reason", "street__name")
    readonly_fields = ("confirmations", "objections", "session_hash", "created_at", "updated_at")


@admin.register(ProposalVote)
class ProposalVoteAdmin(admin.ModelAdmin):
    list_display = ("proposal", "is_support", "created_at")
    list_filter = ("is_support",)


@admin.register(QuorumRule)
class QuorumRuleAdmin(admin.ModelAdmin):
    list_display = (
        "change_kind", "waste_type", "min_confirmations", "requires_source",
        "window_days", "auto_publish", "is_active",
    )
    list_filter = ("change_kind", "is_active", "auto_publish")


@admin.register(CommunityContribution)
class CommunityContributionAdmin(admin.ModelAdmin):
    list_display = ("waste_type", "year", "date", "zone_code", "street_text", "status", "created_at")
    list_filter = ("status", "waste_type", "year")
    search_fields = ("street_text", "note")
