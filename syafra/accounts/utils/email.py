import logging
from email.utils import parseaddr

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.validators import validate_email
from django.template.loader import render_to_string

from accounts.email_tracking import (
    build_custom_args,
    create_email_log,
    get_recent_order_email_issue,
    mark_email_accepted,
    mark_email_attempt,
    mark_email_failed,
)
from accounts.models import EmailLog
from accounts.services.email_service import EmailService
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


def _build_resend_sender(from_email):
    display_name, email_address = parseaddr(from_email or "")
    if not email_address:
        email_address = settings.DEFAULT_FROM_EMAIL
    if display_name:
        return f"{display_name} <{email_address}>"
    return email_address


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


def _send_via_resend_sdk(email_log, *, subject, message, recipient, html_message=None, from_email=None):
    tags = [{"name": "email_type", "value": email_log.email_type}]
    if email_log.event_type:
        tags.append({"name": "event_type", "value": email_log.event_type})

    custom_args = build_custom_args(email_log)
    headers = None
    if custom_args:
        headers = {f"X-Syafra-{k}": str(v) for k, v in custom_args.items()}

    success, elapsed_ms, error, message_id, is_retryable = EmailService.send(
        to=recipient,
        subject=subject,
        text=message,
        html=html_message,
        from_email=from_email,
        tags=tags,
        headers=headers,
    )

    if success:
        logger.info(
            "Resend accepted | email_log_id=%s | recipient=%s | message_id=%s | elapsed=%.1fms",
            email_log.id, recipient, message_id, elapsed_ms,
        )
        mark_email_accepted(
            email_log,
            response_status=200,
            message_id=message_id,
            provider_response=f"accepted in {elapsed_ms:.0f}ms",
            elapsed_ms=elapsed_ms,
        )
    else:
        logger.error(
            "Resend API error | email_log_id=%s | recipient=%s | elapsed=%.1fms | error=%s",
            email_log.id, recipient, elapsed_ms, error,
        )
        mark_email_failed(
            email_log,
            error_message=error or "Unknown error",
            provider_response=f"failed in {elapsed_ms:.0f}ms",
            elapsed_ms=elapsed_ms,
            retryable=is_retryable,
        )

    return success


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

            sent = _send_via_resend_sdk(
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
                "Resend exception | email_log_id=%s | recipient=%s | attempt=%s | order_id=%s | user_id=%s",
                email_log.id,
                recipient,
                attempt,
                email_log.order_id or "-",
                email_log.user_id or "-",
            )

        email_log.refresh_from_db(fields=["retryable"])
        if not email_log.retryable or attempt >= attempts:
            return False

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

    The production path uses the Resend SDK directly and records delivery
    attempts in EmailLog. Explicit Django backend overrides remain available for
    tests and local diagnostics.
    """
    if isinstance(recipient_list, str):
        recipient_list = [recipient_list]

    if not recipient_list:
        logger.warning("EMAIL SKIPPED | subject=%s | no recipients", subject)
        return False

    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    # Defensive guard: ensure the from domain is a verified syafra.com address
    _name, _addr = parseaddr(str(from_email))
    if _addr and not _addr.lower().endswith("@syafra.com"):
        logger.critical(
            "OVERRIDING unverified from_email in send_email | original=%s | new=%s",
            from_email, settings.DEFAULT_FROM_EMAIL,
        )
        from_email = settings.DEFAULT_FROM_EMAIL

    logger.info(
        "EMAIL SEND REQUEST | from=%s | subject=%s | to=%s | backend=%s | email_type=%s | order_id=%s | user_id=%s",
        from_email,
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
            "EMAIL SENT SUCCESS | from=%s | subject=%s | recipients=%s | email_type=%s | order_id=%s | user_id=%s",
            from_email,
            subject,
            recipient_list,
            email_type,
            getattr(order, "pk", None) or "-",
            getattr(user, "pk", None) or "-",
        )
    else:
        logger.error(
            "EMAIL FAILED | from=%s | subject=%s | recipients=%s | email_type=%s | order_id=%s | user_id=%s",
            from_email,
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
            "uid": uidb64,
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
        "resend_api_key_configured": bool(getattr(settings, "RESEND_API_KEY", "")),
        "debug_mode": settings.DEBUG,
    }

    if _using_django_backend():
        diagnostics["warning"] = "Using Django email backend override - useful for tests or local debugging"
    else:
        diagnostics["warning"] = "Using direct Resend SDK delivery"
        diagnostics["api_connection"] = "Configured" if diagnostics["resend_api_key_configured"] else "Missing API key"

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
