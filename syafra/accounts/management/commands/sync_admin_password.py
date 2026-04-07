import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Create or synchronize a superuser password from environment variables during deploy. "
        "No-op unless ADMIN_PASSWORD_RESET_PASSWORD is set."
    )

    def handle(self, *args, **options):
        password = os.getenv("ADMIN_PASSWORD_RESET_PASSWORD", "").strip()
        requested_username = os.getenv("ADMIN_PASSWORD_RESET_USERNAME", "").strip()
        requested_email = os.getenv("ADMIN_PASSWORD_RESET_EMAIL", "").strip()

        if not password:
            self.stdout.write(
                self.style.NOTICE(
                    "ADMIN_PASSWORD_RESET_PASSWORD is not set; skipping admin password sync."
                )
            )
            return

        User = get_user_model()
        target_username = requested_username or "admin"

        def create_superuser(username: str):
            create_kwargs = {"username": username, "password": password}
            if "email" in {field.name for field in User._meta.fields}:
                create_kwargs["email"] = requested_email
            user = User.objects.create_superuser(**create_kwargs)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created superuser '{user.username}'."
                )
            )
            return user

        if requested_username:
            try:
                user = User.objects.get(username=target_username)
            except User.DoesNotExist:
                user = create_superuser(target_username)
            else:
                updates = []
                if not user.is_staff:
                    user.is_staff = True
                    updates.append("is_staff")
                if not user.is_superuser:
                    user.is_superuser = True
                    updates.append("is_superuser")
                if hasattr(user, "is_active") and not user.is_active:
                    user.is_active = True
                    updates.append("is_active")
                if updates:
                    user.save(update_fields=updates)
        else:
            try:
                user = User.objects.get(username="admin", is_superuser=True)
            except User.DoesNotExist:
                superusers = list(User.objects.filter(is_superuser=True).order_by("id"))
                if len(superusers) == 1:
                    user = superusers[0]
                elif not superusers:
                    user = create_superuser("admin")
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
