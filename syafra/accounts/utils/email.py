import logging
import time
from email.utils import parseaddr

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.validators import validate_email
from django.template.loader import render_to_string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import From, Mail

from accounts.email_tracking import (
    RETRYABLE_SENDGRID_STATUS_CODES,
    build_custom_args,
    create_email_log,
    get_recent_order_email_issue,
    mark_email_accepted,
    mark_email_attempt,
    mark_email_failed,
)
from accounts.models import EmailLog
from syafra.logging_context import get_correlation_id

logger = logging.getLogger("syafra.email")

DJANGO_BACKEND_PREFIX = "django.core.mail.backends."


def _normalize_recipients(recipient_list):
    normalized = []
    seen = set()
    for recipient in recipient_list or []:
        cleaned = (recipient or "").strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def _using_django_backend():
    return str(getattr(settings, "EMAIL_BACKEND", "")).startswith(DJANGO_BACKEND_PREFIX)


def _read_sendgrid_body(response):
    body = getattr(response, "body", "")
    if isinstance(body, bytes):
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError:
            return body.decode("utf-8", errors="replace")
    return str(body)


def _get_sendgrid_message_id(response):
    headers = getattr(response, "headers", None)
    if headers is None:
        return ""
    if hasattr(headers, "get"):
        return (
            headers.get("X-Message-Id")
            or headers.get("x-message-id")
            or headers.get("X-Message-ID")
            or ""
        )
    return ""


def _build_sendgrid_sender(from_email):
    display_name, email_address = parseaddr(from_email or "")
    if not email_address:
        fallback_sender = (getattr(settings, "SENDGRID_SENDER_EMAIL", "") or "").strip()
        if not fallback_sender:
            raise ValueError("SENDGRID_SENDER_EMAIL is missing")
        email_address = fallback_sender
    if display_name:
        return From(email_address, display_name)
    return From(email_address)


def _build_log_metadata(*, email_type, user=None, order=None, metadata=None):
    payload = {
        "email_type": email_type,
    }
    if user is not None:
        payload["user_id"] = user.pk
    if order is not None:
        payload["order_id"] = order.pk
    if metadata:
        payload.update(metadata)
    return payload


def _send_via_django_backend(subject, message, recipient_list, html_message=None, from_email=None):
    if html_message:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=recipient_list,
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
        return True

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=False,
    )
    return True


def _send_via_sendgrid_sdk(email_log, *, subject, message, recipient, html_message=None, from_email=None):
    api_key = (getattr(settings, "SENDGRID_API_KEY", "") or "").strip()
    if not api_key:
        raise ValueError("SENDGRID_API_KEY is missing")

    sender = _build_sendgrid_sender(from_email)
    client = SendGridAPIClient(api_key)
    html_content = html_message or message.replace("\n", "<br>")

    mail = Mail(
        from_email=sender,
        to_emails=recipient,
        subject=subject,
        plain_text_content=message,
        html_content=html_content,
    )
    for key, value in build_custom_args(email_log).items():
        mail.add_custom_arg({key: str(value)})

    response = client.send(mail)
    response_body = _read_sendgrid_body(response)

    logger.info(
        "SendGrid Status: %s | email_log_id=%s | recipient=%s | order_id=%s | user_id=%s",
        response.status_code,
        email_log.id,
        recipient,
        email_log.order_id or "-",
        email_log.user_id or "-",
    )

    if response.status_code >= 400:
        logger.error(
            "SendGrid Error Body: %s | email_log_id=%s | recipient=%s",
            response_body,
            email_log.id,
            recipient,
        )
        mark_email_failed(
            email_log,
            error_message=f"SendGrid API returned status {response.status_code}",
            response_status=response.status_code,
            provider_response=response_body,
            retryable=response.status_code in RETRYABLE_SENDGRID_STATUS_CODES,
        )
        return False

    mark_email_accepted(
        email_log,
        response_status=response.status_code,
        message_id=_get_sendgrid_message_id(response),
        provider_response=response_body,
    )
    return True


def _is_retryable_exception(exc):
    if isinstance(exc, ValueError):
        return False
    return isinstance(exc, (ConnectionError, TimeoutError, OSError))


def _send_single_email(
    *,
    recipient,
    subject,
    message,
    html_message=None,
    from_email=None,
    email_type=EmailLog.TYPE_GENERIC,
    event_type="",
    user=None,
    order=None,
    correlation_id=None,
    metadata=None,
    max_retries=None,
):
    correlation_id = correlation_id or get_correlation_id()
    email_log = create_email_log(
        recipient=recipient,
        subject=subject,
        email_type=email_type,
        event_type=event_type,
        user=user,
        order=order,
        correlation_id=correlation_id,
        metadata=_build_log_metadata(
            email_type=email_type,
            user=user,
            order=order,
            metadata=metadata,
        ),
    )

    try:
        validate_email(recipient)
    except ValidationError:
        logger.error(
            "Invalid recipient email skipped | email_log_id=%s | recipient=%s | order_id=%s | user_id=%s",
            email_log.id,
            recipient,
            email_log.order_id or "-",
            email_log.user_id or "-",
        )
        mark_email_failed(
            email_log,
            error_message="Invalid recipient email address.",
            retryable=False,
        )
        return False

    attempts = max_retries if max_retries is not None else max(getattr(settings, "EMAIL_SIMPLE_RETRY_ATTEMPTS", 2), 1)
    base_delay = max(getattr(settings, "EMAIL_SIMPLE_RETRY_BASE_DELAY_SECONDS", 1), 0)

    for attempt in range(1, attempts + 1):
        mark_email_attempt(email_log)
        try:
            if _using_django_backend():
                _send_via_django_backend(
                    subject,
                    message,
                    [recipient],
                    html_message=html_message,
                    from_email=from_email,
                )
                mark_email_accepted(email_log, response_status=200)
                return True

            sent = _send_via_sendgrid_sdk(
                email_log,
                subject=subject,
                message=message,
                recipient=recipient,
                html_message=html_message,
                from_email=from_email,
            )
            if sent:
                return True
        except Exception as exc:
            retryable = _is_retryable_exception(exc)
            mark_email_failed(
                email_log,
                error_message=str(exc),
                retryable=retryable,
            )
            logger.exception(
                "SendGrid Exception occurred | email_log_id=%s | recipient=%s | attempt=%s | order_id=%s | user_id=%s",
                email_log.id,
                recipient,
                attempt,
                email_log.order_id or "-",
                email_log.user_id or "-",
            )

        email_log.refresh_from_db(fields=["retryable"])
        if not email_log.retryable or attempt >= attempts:
            return False
        if base_delay:
            time.sleep(base_delay * attempt)

    return False


def send_email(
    subject,
    message,
    recipient_list,
    html_message=None,
    from_email=None,
    *,
    email_type=EmailLog.TYPE_GENERIC,
    event_type="",
    user=None,
    order=None,
    correlation_id=None,
    metadata=None,
    max_retries=None,
):
    """
    Send an email with optional HTML content.

    The production path uses the SendGrid SDK directly and records delivery
    attempts in EmailLog. Explicit Django backend overrides remain available for
    tests and local diagnostics.
    """
    recipient_list = _normalize_recipients(recipient_list)
    if not recipient_list:
        logger.warning("EMAIL SKIPPED | subject=%s | no recipients", subject)
        return False

    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    logger.info(
        "EMAIL SEND REQUEST | subject=%s | to=%s | backend=%s | email_type=%s | order_id=%s | user_id=%s",
        subject,
        recipient_list,
        settings.EMAIL_BACKEND,
        email_type,
        getattr(order, "pk", None) or "-",
        getattr(user, "pk", None) or "-",
    )

    results = []
    for recipient in recipient_list:
        results.append(
            _send_single_email(
                recipient=recipient,
                subject=subject,
                message=message,
                html_message=html_message,
                from_email=from_email,
                email_type=email_type,
                event_type=event_type,
                user=user,
                order=order,
                correlation_id=correlation_id,
                metadata=metadata,
                max_retries=max_retries,
            )
        )

    sent = all(results)
    if sent:
        logger.info(
            "EMAIL SENT SUCCESS | subject=%s | recipients=%s | email_type=%s | order_id=%s | user_id=%s",
            subject,
            recipient_list,
            email_type,
            getattr(order, "pk", None) or "-",
            getattr(user, "pk", None) or "-",
        )
    else:
        logger.error(
            "EMAIL FAILED | subject=%s | recipients=%s | email_type=%s | order_id=%s | user_id=%s",
            subject,
            recipient_list,
            email_type,
            getattr(order, "pk", None) or "-",
            getattr(user, "pk", None) or "-",
        )
    return sent


def send_password_reset_email(user, request=None):
    """
    Send password reset email to user.
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.urls import reverse
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    try:
        if request:
            protocol = "https" if getattr(settings, "USE_HTTPS", request.is_secure()) else "http"
            domain = getattr(settings, "DOMAIN", "").strip() or request.get_host()
        else:
            protocol = "https" if settings.USE_HTTPS else "http"
            domain = getattr(settings, "DOMAIN", "").strip() or "localhost"

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{protocol}://{domain}{reverse('accounts:password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})}"

        context = {
            "user": user,
            "reset_url": reset_url,
            "protocol": protocol,
            "domain": domain,
            "uidb64": uidb64,
            "token": token,
        }

        subject = render_to_string("registration/password_reset_subject.txt").strip()
        html_message = render_to_string("registration/password_reset_email.html", context)
        plain_message = f"""
Hello {user.username or user.email},

You have requested a password reset for your SYAFRA account.

Click the link below to reset your password:
{reset_url}

If you did not request this, you can ignore this email.

Thanks,
SYAFRA Team
        """.strip()

        sent = send_email(
            subject=subject,
            message=plain_message,
            recipient_list=[user.email],
            html_message=html_message,
            email_type=EmailLog.TYPE_PASSWORD_RESET,
            user=user,
            metadata={"flow": "password_reset"},
        )
        if not sent:
            return False

        logger.info("Password reset email sent to %s", user.email)
        return True
    except Exception as exc:
        logger.error("Failed to send password reset email to %s: %s", user.email, exc)
        return False


def test_email_configuration():
    diagnostics = {
        "backend": settings.EMAIL_BACKEND,
        "from_email": settings.DEFAULT_FROM_EMAIL,
        "sendgrid_sender": getattr(settings, "SENDGRID_SENDER_EMAIL", "Not configured"),
        "sendgrid_api_key_configured": bool(getattr(settings, "SENDGRID_API_KEY", "")),
        "sendgrid_webhook_verification_key_configured": bool(
            getattr(settings, "SENDGRID_EVENT_WEBHOOK_VERIFICATION_KEY", "")
        ),
        "debug_mode": settings.DEBUG,
    }

    if _using_django_backend():
        diagnostics["warning"] = "Using Django email backend override - useful for tests or local debugging"
    else:
        diagnostics["warning"] = "Using direct SendGrid SDK delivery"
        diagnostics["api_connection"] = "Configured" if diagnostics["sendgrid_api_key_configured"] else "Missing API key"

    return diagnostics


def send_test_email(recipient):
    return send_email(
        subject="Test Email from SYAFRA",
        message="This is a test email to verify email configuration is working.",
        recipient_list=[recipient],
        html_message="<h1>Test Email</h1><p>This is a test email from SYAFRA.</p>",
        email_type=EmailLog.TYPE_TEST,
        metadata={"flow": "manual_test"},
    )


def recent_order_email_issue(order):
    return get_recent_order_email_issue(order)
