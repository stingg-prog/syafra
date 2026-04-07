import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Synchronize a superuser password from environment variables during deploy. "
        "No-op unless ADMIN_PASSWORD_RESET_PASSWORD is set."
    )

    def handle(self, *args, **options):
        password = os.getenv("ADMIN_PASSWORD_RESET_PASSWORD", "").strip()
        requested_username = os.getenv("ADMIN_PASSWORD_RESET_USERNAME", "").strip()

        if not password:
            self.stdout.write(
                self.style.NOTICE(
                    "ADMIN_PASSWORD_RESET_PASSWORD is not set; skipping admin password sync."
                )
            )
            return

        User = get_user_model()

        if requested_username:
            try:
                user = User.objects.get(username=requested_username, is_superuser=True)
            except User.DoesNotExist as exc:
                raise CommandError(
                    f"Superuser '{requested_username}' was not found."
                ) from exc
        else:
            try:
                user = User.objects.get(username="admin", is_superuser=True)
            except User.DoesNotExist:
                superusers = list(User.objects.filter(is_superuser=True).order_by("id"))
                if len(superusers) == 1:
                    user = superusers[0]
                elif not superusers:
                    raise CommandError(
                        "No superuser exists. Create one first or set "
                        "ADMIN_PASSWORD_RESET_USERNAME to an existing superuser."
                    )
                else:
                    raise CommandError(
                        "Multiple superusers exist. Set ADMIN_PASSWORD_RESET_USERNAME "
                        "to choose which account to reset."
                    )

        user.set_password(password)
        user.save(update_fields=["password"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated password for superuser '{user.username}'."
            )
        )
