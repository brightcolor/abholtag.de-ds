from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.community.models import CorrectionProposal, ProposalStatus, QuorumRule
from apps.notifications.services import notify_admins


class Command(BaseCommand):
    help = (
        "Wertet offene Korrekturvorschläge gegen die Quorum-Regeln aus (§22). "
        "Erreichte Quoren werden markiert; automatische Veröffentlichung erfolgt "
        "nur bei aktiviertem Community-Modus und Regel-Flag."
    )

    def handle(self, *args, **options):
        open_proposals = CorrectionProposal.objects.filter(
            status__in=[ProposalStatus.SUBMITTED, ProposalStatus.AWAITING_CONFIRMATION]
        )
        reached = 0
        for proposal in open_proposals:
            rule = self._rule_for(proposal)
            if rule is None:
                continue
            window_start = timezone.now() - timedelta(days=rule.window_days)
            votes = proposal.votes.filter(created_at__gte=window_start)
            supports = votes.filter(is_support=True).count()
            objections = votes.filter(is_support=False).count()
            total = supports + objections

            if supports < rule.min_confirmations:
                continue
            if total and objections / total > rule.max_objection_ratio:
                continue
            if rule.requires_source and not proposal.source_url:
                continue

            proposal.status = ProposalStatus.QUORUM_REACHED
            proposal.save(update_fields=["status", "updated_at"])
            reached += 1
            notify_admins(
                f"Quorum erreicht: Vorschlag #{proposal.pk}",
                f"{proposal.get_kind_display()} – {supports} Bestätigungen, {objections} Gegenstimmen.\n"
                "Bitte im Moderationsbereich prüfen.",
            )
            if settings.COMMUNITY_MODE_ENABLED and settings.COMMUNITY_AUTO_PUBLISH and rule.auto_publish:
                self.stdout.write(
                    f"  Vorschlag #{proposal.pk}: automatische Veröffentlichung ist aktiviert, "
                    "Umsetzung erfolgt durch die Moderation (Anwenden der Änderung)."
                )

        self.stdout.write(self.style.SUCCESS(f"{reached} Vorschläge haben das Quorum erreicht."))

    @staticmethod
    def _rule_for(proposal) -> QuorumRule | None:
        rules = QuorumRule.objects.filter(change_kind=proposal.kind, is_active=True)
        specific = rules.filter(waste_type=proposal.waste_type).first()
        return specific or rules.filter(waste_type__isnull=True).first()
