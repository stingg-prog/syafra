from django.core.management.base import BaseCommand

from syafra_agent.actions import expire_pending_proposals


class Command(BaseCommand):
    help = "Remove expired, unconfirmed Syafra AI previews and their private image files."

    def handle(self, *args, **options):
        expire_pending_proposals()
        self.stdout.write(self.style.SUCCESS("Expired Syafra AI previews cleaned up."))
