from django.apps import AppConfig


class SyafraConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "syafra"

    def ready(self):
        pass
