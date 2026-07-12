"""Admin for community features."""
from django.contrib import admin
from .models import ErrorReport, CorrectionProposal, ProposalVote, QuorumRule, CommunityContribution

@admin.register(ErrorReport)
class ErrorReportAdmin(admin.ModelAdmin):
    list_display = ["public_id", "category", "status", "affected_street", "created_at"]
    list_filter = ["status", "category"]
    search_fields = ["public_id", "description"]
    readonly_fields = ["public_id"]

@admin.register(CorrectionProposal)
class CorrectionProposalAdmin(admin.ModelAdmin):
    list_display = ["public_id", "target_type", "status", "confidence", "votes_yes", "votes_no"]
    list_filter = ["status", "target_type"]
    search_fields = ["public_id", "reason"]
    readonly_fields = ["public_id"]

@admin.register(ProposalVote)
class ProposalVoteAdmin(admin.ModelAdmin):
    list_display = ["proposal", "vote", "voter", "created_at"]
    list_filter = ["vote"]

@admin.register(QuorumRule)
class QuorumRuleAdmin(admin.ModelAdmin):
    list_display = ["waste_type", "target_type", "min_votes", "voting_period_days"]
    list_filter = ["waste_type"]

@admin.register(CommunityContribution)
class CommunityContributionAdmin(admin.ModelAdmin):
    list_display = ["public_id", "waste_type", "collection_date", "street", "status"]
    list_filter = ["status", "waste_type"]
    search_fields = ["public_id"]