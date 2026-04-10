from django.conf import settings
from django.db import models
from django.db.models import Q


class EmailLog(models.Model):
    PROVIDER_SENDGRID = "sendgrid"

    STATUS_QUEUED = "queued"
    STATUS_ACCEPTED = "accepted"
    STATUS_FAILED = "failed"
    STATUS_DELIVERED = "delivered"
    STATUS_DEFERRED = "deferred"
    STATUS_DROPPED = "dropped"
    STATUS_BOUNCED = "bounced"
    STATUS_BLOCKED = "blocked"
    STATUS_OPENED = "opened"
    STATUS_SPAM_REPORTED = "spam_report"

    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_FAILED, "Failed"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_DEFERRED, "Deferred"),
        (STATUS_DROPPED, "Dropped"),
        (STATUS_BOUNCED, "Bounced"),
        (STATUS_BLOCKED, "Blocked"),
        (STATUS_OPENED, "Opened"),
        (STATUS_SPAM_REPORTED, "Spam Reported"),
    ]

    TYPE_GENERIC = "generic"
    TYPE_PASSWORD_RESET = "password_reset"
    TYPE_ACCOUNT_ACTIVATION = "account_activation"
    TYPE_ORDER_CONFIRMATION = "order_confirmation"
    TYPE_PAYMENT_CONFIRMATION = "payment_confirmation"
    TYPE_ORDER_STATUS = "order_status"
    TYPE_ADMIN_ORDER_ALERT = "admin_order_alert"
    TYPE_TEST = "test_email"

    EMAIL_TYPE_CHOICES = [
        (TYPE_GENERIC, "Generic"),
        (TYPE_PASSWORD_RESET, "Password Reset"),
        (TYPE_ACCOUNT_ACTIVATION, "Account Activation"),
        (TYPE_ORDER_CONFIRMATION, "Order Confirmation"),
        (TYPE_PAYMENT_CONFIRMATION, "Payment Confirmation"),
        (TYPE_ORDER_STATUS, "Order Status"),
        (TYPE_ADMIN_ORDER_ALERT, "Admin Order Alert"),
        (TYPE_TEST, "Test Email"),
    ]

    provider = models.CharField(max_length=32, default=PROVIDER_SENDGRID, db_index=True)
    email_type = models.CharField(max_length=64, choices=EMAIL_TYPE_CHOICES, default=TYPE_GENERIC, db_index=True)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_logs",
    )
    recipient = models.EmailField(db_index=True)
    recipient_domain = models.CharField(max_length=255, blank=True, default="", db_index=True)
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    event_type = models.CharField(max_length=64, blank=True, default="", db_index=True)
    correlation_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    sendgrid_message_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    sendgrid_response_status = models.PositiveIntegerField(null=True, blank=True)
    send_attempts = models.PositiveIntegerField(default=0)
    open_count = models.PositiveIntegerField(default=0)
    retryable = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default="")
    provider_response = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    last_webhook_payload = models.JSONField(default=dict, blank=True)
    last_event_type = models.CharField(max_length=64, blank=True, default="")
    accepted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    deferred_at = models.DateTimeField(null=True, blank=True)
    dropped_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    spam_reported_at = models.DateTimeField(null=True, blank=True)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    last_event_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="email_logs_status_created_idx"),
            models.Index(fields=["email_type", "-created_at"], name="email_logs_type_created_idx"),
            models.Index(fields=["order", "-created_at"], name="email_logs_order_created_idx"),
            models.Index(fields=["user", "-created_at"], name="email_logs_user_created_idx"),
            models.Index(fields=["recipient", "status"], name="email_logs_rcpt_status_idx"),
        ]

    def __str__(self):
        return f"{self.get_email_type_display()} -> {self.recipient} ({self.status})"


class EmailWebhookEvent(models.Model):
    email_log = models.ForeignKey(
        EmailLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="webhook_events",
    )
    provider = models.CharField(max_length=32, default=EmailLog.PROVIDER_SENDGRID, db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    sendgrid_event_id = models.CharField(max_length=255, blank=True, default="")
    sendgrid_message_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    recipient = models.EmailField(blank=True, default="", db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["sendgrid_event_id"],
                condition=~Q(sendgrid_event_id=""),
                name="email_webhook_events_unique_sendgrid_event_id",
            ),
        ]
        indexes = [
            models.Index(fields=["event_type", "-occurred_at"], name="email_webhook_event_type_idx"),
            models.Index(fields=["email_log", "-occurred_at"], name="email_webhook_email_log_idx"),
        ]

    def __str__(self):
        target = self.recipient or "unknown-recipient"
        return f"{self.event_type} -> {target}"
