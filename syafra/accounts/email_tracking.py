from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

from .models import EmailLog, EmailWebhookEvent

NON_RETRYABLE_DELIVERY_STATUSES = {
    EmailLog.STATUS_DROPPED,
    EmailLog.STATUS_BOUNCED,
    EmailLog.STATUS_BLOCKED,
    EmailLog.STATUS_SPAM_REPORTED,
}


def _recipient_domain(recipient):
    if "@" not in recipient:
        return ""
    return recipient.rsplit("@", 1)[-1].lower()


def build_custom_args(email_log):
    custom_args = {
        "email_log_id": str(email_log.id),
        "email_type": email_log.email_type,
    }
    if email_log.event_type:
        custom_args["event_type"] = email_log.event_type
    if email_log.correlation_id:
        custom_args["correlation_id"] = email_log.correlation_id
    if email_log.order_id:
        custom_args["order_id"] = str(email_log.order_id)
    if email_log.user_id:
        custom_args["user_id"] = str(email_log.user_id)
    return custom_args


def create_email_log(*, recipient, subject, email_type=EmailLog.TYPE_GENERIC, event_type="", user=None, order=None, correlation_id="", metadata=None):
    return EmailLog.objects.create(
        email_type=email_type or EmailLog.TYPE_GENERIC,
        event_type=(event_type or "")[:64],
        user=user,
        order=order,
        recipient=recipient,
        recipient_domain=_recipient_domain(recipient),
        subject=subject[:255],
        status=EmailLog.STATUS_QUEUED,
        correlation_id=(correlation_id or "")[:64],
        metadata=metadata or {},
    )


def mark_email_attempt(email_log):
    email_log.send_attempts += 1
    if email_log.send_attempts > 1:
        email_log.last_retry_at = timezone.now()
    email_log.save(update_fields=["send_attempts", "last_retry_at", "updated_at"])


def mark_email_accepted(email_log, *, response_status, message_id="", provider_response="", elapsed_ms=None):
    email_log.status = EmailLog.STATUS_ACCEPTED
    email_log.retryable = False
    email_log.provider_response_status = response_status
    email_log.provider_message_id = (message_id or "")[:255]
    email_log.provider_response = provider_response or ""
    email_log.error_message = ""
    email_log.accepted_at = timezone.now()
    email_log.save(
        update_fields=[
            "status",
            "retryable",
            "provider_response_status",
            "provider_message_id",
            "provider_response",
            "error_message",
            "accepted_at",
            "updated_at",
        ]
    )
    if elapsed_ms is not None:
        meta = dict(email_log.metadata or {})
        meta["send_elapsed_ms"] = round(elapsed_ms, 1)
        EmailLog.objects.filter(pk=email_log.pk).update(metadata=meta)
    return email_log


def mark_email_failed(email_log, *, error_message, response_status=None, provider_response="", retryable=False, elapsed_ms=None):
    email_log.status = EmailLog.STATUS_FAILED
    email_log.retryable = retryable
    email_log.error_message = error_message or ""
    email_log.provider_response = provider_response or ""
    if response_status is not None:
        email_log.provider_response_status = response_status
    email_log.save(
        update_fields=[
            "status",
            "retryable",
            "error_message",
            "provider_response",
            "provider_response_status",
            "updated_at",
        ]
    )
    if elapsed_ms is not None:
        meta = dict(email_log.metadata or {})
        meta["send_elapsed_ms"] = round(elapsed_ms, 1)
        EmailLog.objects.filter(pk=email_log.pk).update(metadata=meta)
    return email_log


def get_recent_order_email_issue(order):
    return (
        EmailLog.objects.filter(
            order=order,
            email_type__in=[
                EmailLog.TYPE_ORDER_CONFIRMATION,
                EmailLog.TYPE_PAYMENT_CONFIRMATION,
            ],
            status__in=[
                EmailLog.STATUS_FAILED,
                EmailLog.STATUS_DROPPED,
                EmailLog.STATUS_BOUNCED,
                EmailLog.STATUS_BLOCKED,
                EmailLog.STATUS_SPAM_REPORTED,
            ],
        )
        .order_by("-updated_at")
        .first()
    )


def latest_retryable_failure(order, email_type):
    return (
        EmailLog.objects.filter(
            order=order,
            email_type=email_type,
            status=EmailLog.STATUS_FAILED,
            retryable=True,
        )
        .order_by("-updated_at")
        .first()
    )
