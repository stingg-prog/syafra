import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone


private_upload_storage = FileSystemStorage(
    location=settings.BASE_DIR / ".agent_private_media"
)


class AgentProposal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="syafra_agent_proposals",
    )
    prompt = models.TextField()
    reply = models.TextField(blank=True)
    actions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()


class AgentAttachment(models.Model):
    proposal = models.ForeignKey(
        AgentProposal,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    storage_path = models.CharField(max_length=500)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()

    class Meta:
        ordering = ["id"]
