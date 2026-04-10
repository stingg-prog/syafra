from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

from .models import EmailLog, EmailWebhookEvent

RETRYABLE_SENDGRID_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
NON_RETRYABLE_DELIVERY_STATUSES = {
    EmailLog.STATUS_DROPPED,
    EmailLog.STATUS_BOUNCED,
    EmailLog.STATUS_BLOCKED,
    EmailLog.STATUS_SPAM_REPORTED,
}
SENDGRID_EVENT_STATUS_MAP = {
    "delivered": EmailLog.STATUS_DELIVERED,
    "deferred": EmailLog.STATUS_DEFERRED,
    "dropped": EmailLog.STATUS_DROPPED,
    "bounce": EmailLog.STATUS_BOUNCED,
    "blocked": EmailLog.STATUS_BLOCKED,
    "open": EmailLog.STATUS_OPENED,
    "spamreport": EmailLog.STATUS_SPAM_REPORTED,
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


def mark_email_accepted(email_log, *, response_status, message_id="", provider_response=""):
    email_log.status = EmailLog.STATUS_ACCEPTED
    email_log.retryable = False
    email_log.sendgrid_response_status = response_status
    email_log.sendgrid_message_id = (message_id or "")[:255]
    email_log.provider_response = provider_response or ""
    email_log.error_message = ""
    email_log.accepted_at = timezone.now()
    email_log.save(
        update_fields=[
            "status",
            "retryable",
            "sendgrid_response_status",
            "sendgrid_message_id",
            "provider_response",
            "error_message",
            "accepted_at",
            "updated_at",
        ]
    )
    return email_log


def mark_email_failed(email_log, *, error_message, response_status=None, provider_response="", retryable=False):
    email_log.status = EmailLog.STATUS_FAILED
    email_log.retryable = retryable
    email_log.error_message = error_message or ""
    email_log.provider_response = provider_response or ""
    if response_status is not None:
        email_log.sendgrid_response_status = response_status
    email_log.save(
        update_fields=[
            "status",
            "retryable",
            "error_message",
            "provider_response",
            "sendgrid_response_status",
            "updated_at",
        ]
    )
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


def _extract_custom_args(event):
    custom_args = event.get("custom_args")
    if isinstance(custom_args, dict):
        return custom_args
    unique_args = event.get("unique_args")
    if isinstance(unique_args, dict):
        return unique_args
    return {}


def _normalize_sendgrid_message_id(value):
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    return cleaned.split(".", 1)[0]


def _coerce_event_time(timestamp_value):
    try:
        return datetime.fromtimestamp(int(timestamp_value), tz=dt_timezone.utc)
    except (TypeError, ValueError, OSError):
        return timezone.now()


def _should_update_last_event(email_log, occurred_at):
    return email_log.last_event_at is None or occurred_at >= email_log.last_event_at


def resolve_email_log_for_event(event):
    custom_args = _extract_custom_args(event)
    email_log_id = custom_args.get("email_log_id") or event.get("email_log_id")
    if email_log_id:
        try:
            return EmailLog.objects.filter(pk=int(email_log_id)).first()
        except (TypeError, ValueError):
            pass

    message_id = _normalize_sendgrid_message_id(event.get("sg_message_id"))
    if message_id:
        email_log = EmailLog.objects.filter(sendgrid_message_id=message_id).first()
        if email_log:
            return email_log
        return EmailLog.objects.filter(sendgrid_message_id__startswith=message_id).first()
    return None


def apply_sendgrid_webhook_event(event):
    event_type = (event.get("event") or "").strip().lower()
    occurred_at = _coerce_event_time(event.get("timestamp"))
    email_log = resolve_email_log_for_event(event)
    custom_args = _extract_custom_args(event)
    message_id = _normalize_sendgrid_message_id(event.get("sg_message_id"))
    recipient = (event.get("email") or "").strip()
    sendgrid_event_id = (event.get("sg_event_id") or "").strip()

    webhook_event = None
    if sendgrid_event_id:
        webhook_event, created = EmailWebhookEvent.objects.get_or_create(
            sendgrid_event_id=sendgrid_event_id,
            defaults={
                "email_log": email_log,
                "event_type": event_type or "unknown",
                "sendgrid_message_id": message_id,
                "recipient": recipient,
                "payload": event,
                "occurred_at": occurred_at,
            },
        )
        if not created:
            return email_log, webhook_event, False
    else:
        webhook_event = EmailWebhookEvent.objects.create(
            email_log=email_log,
            event_type=event_type or "unknown",
            sendgrid_message_id=message_id,
            recipient=recipient,
            payload=event,
            occurred_at=occurred_at,
        )

    if email_log is None:
        return None, webhook_event, True

    status = SENDGRID_EVENT_STATUS_MAP.get(event_type)
    update_fields = ["updated_at"]
    should_update_last_event = _should_update_last_event(email_log, occurred_at)
    if should_update_last_event:
        email_log.last_event_type = event_type
        email_log.last_event_at = occurred_at
        email_log.last_webhook_payload = event
        update_fields.extend(["last_event_type", "last_event_at", "last_webhook_payload"])
    if message_id and not email_log.sendgrid_message_id:
        email_log.sendgrid_message_id = message_id
        update_fields.append("sendgrid_message_id")

    reason = (event.get("reason") or event.get("response") or "").strip()
    if status == EmailLog.STATUS_DELIVERED:
        if not should_update_last_event:
            return email_log, webhook_event, True
        email_log.status = status
        email_log.delivered_at = occurred_at
        email_log.retryable = False
        email_log.error_message = ""
        update_fields.extend(["status", "delivered_at", "error_message", "retryable"])
    elif status == EmailLog.STATUS_DEFERRED:
        if not should_update_last_event:
            return email_log, webhook_event, True
        email_log.status = status
        email_log.deferred_at = occurred_at
        email_log.retryable = False
        email_log.error_message = reason
        update_fields.extend(["status", "deferred_at", "error_message", "retryable"])
    elif status == EmailLog.STATUS_DROPPED:
        if not should_update_last_event:
            return email_log, webhook_event, True
        email_log.status = status
        email_log.dropped_at = occurred_at
        email_log.retryable = False
        email_log.error_message = reason
        update_fields.extend(["status", "dropped_at", "error_message", "retryable"])
    elif status == EmailLog.STATUS_BOUNCED:
        if not should_update_last_event:
            return email_log, webhook_event, True
        email_log.status = status
        email_log.bounced_at = occurred_at
        email_log.retryable = False
        email_log.error_message = reason
        update_fields.extend(["status", "bounced_at", "error_message", "retryable"])
    elif status == EmailLog.STATUS_BLOCKED:
        if not should_update_last_event:
            return email_log, webhook_event, True
        email_log.status = status
        email_log.blocked_at = occurred_at
        email_log.retryable = False
        email_log.error_message = reason
        update_fields.extend(["status", "blocked_at", "error_message", "retryable"])
    elif status == EmailLog.STATUS_OPENED:
        email_log.open_count += 1
        if email_log.opened_at is None:
            email_log.opened_at = occurred_at
            update_fields.append("opened_at")
        update_fields.append("open_count")
    elif status == EmailLog.STATUS_SPAM_REPORTED:
        if not should_update_last_event:
            return email_log, webhook_event, True
        email_log.status = status
        email_log.spam_reported_at = occurred_at
        email_log.retryable = False
        email_log.error_message = reason or "Recipient marked this email as spam."
        update_fields.extend(["status", "spam_reported_at", "error_message", "retryable"])

    email_log.save(update_fields=list(dict.fromkeys(update_fields)))
    if webhook_event.email_log_id != email_log.id:
        webhook_event.email_log = email_log
        webhook_event.save(update_fields=["email_log"])
    return email_log, webhook_event, True
