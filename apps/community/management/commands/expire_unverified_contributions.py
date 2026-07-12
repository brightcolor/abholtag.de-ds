from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.community.models import CommunityContribution, ContributionStatus


class Command(BaseCommand):
    help = "Markiert alte, nie geprüfte Community-Beiträge als verfallen."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=180)

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        updated = CommunityContribution.objects.filter(
            status=ContributionStatus.SUBMITTED, created_at__lt=cutoff
        ).update(status=ContributionStatus.EXPIRED)
        self.stdout.write(self.style.SUCCESS(f"{updated} Beiträge als verfallen markiert."))
