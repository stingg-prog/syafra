from django.contrib import admin

from .models import EmailLog, EmailWebhookEvent


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email_type",
        "recipient",
        "status",
        "send_attempts",
        "retryable",
        "sendgrid_response_status",
        "order",
        "user",
        "created_at",
        "last_event_at",
    )
    list_filter = ("status", "email_type", "provider", "retryable", "created_at")
    search_fields = (
        "recipient",
        "subject",
        "event_type",
        "sendgrid_message_id",
        "correlation_id",
        "order__id",
        "user__username",
        "user__email",
    )
    readonly_fields = (
        "provider",
        "email_type",
        "recipient",
        "recipient_domain",
        "subject",
        "status",
        "event_type",
        "correlation_id",
        "sendgrid_message_id",
        "sendgrid_response_status",
        "send_attempts",
        "open_count",
        "retryable",
        "error_message",
        "provider_response",
        "metadata",
        "last_webhook_payload",
        "last_event_type",
        "accepted_at",
        "delivered_at",
        "deferred_at",
        "dropped_at",
        "bounced_at",
        "blocked_at",
        "opened_at",
        "spam_reported_at",
        "last_retry_at",
        "last_event_at",
        "created_at",
        "updated_at",
    )
    list_select_related = ("order", "user")


@admin.register(EmailWebhookEvent)
class EmailWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_type",
        "recipient",
        "email_log",
        "sendgrid_event_id",
        "occurred_at",
        "created_at",
    )
    list_filter = ("event_type", "provider", "occurred_at")
    search_fields = ("recipient", "sendgrid_event_id", "sendgrid_message_id", "email_log__recipient")
    readonly_fields = (
        "email_log",
        "provider",
        "event_type",
        "sendgrid_event_id",
        "sendgrid_message_id",
        "recipient",
        "payload",
        "occurred_at",
        "created_at",
    )
