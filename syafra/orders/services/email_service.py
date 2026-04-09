"""
Production-safe email helpers.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

FORCE_EMAIL_RETRY = getattr(settings, 'FORCE_EMAIL_RETRY', False)


class EmailDeliveryError(Exception):
    """Raised when an email send should be retried."""


def get_currency_symbol():
    """Get currency symbol from payment settings."""
    from orders.models import PaymentSettings

    payment_settings = PaymentSettings.get_settings()
    return payment_settings.currency_symbol if payment_settings else '\u20b9'


def _get_email_claim_timeout():
    return timedelta(seconds=max(getattr(settings, 'ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS', 900), 1))


def _build_order_email_context(order, **extra_context):
    currency = get_currency_symbol()
    context = {
        'order': order,
        'items': order.items.select_related('product').all(),
        'currency': currency,
        'customer_name': order.customer_name,
        'order_date': order.created_at,
        'payment': order.latest_payment,
        'store_email': settings.DEFAULT_FROM_EMAIL,
    }
    context.update(extra_context)
    return context


def _send_html_email(*, subject, template_name, context, recipient_list):
    if not recipient_list:
        logger.warning("Skipping email because no recipients were provided | subject=%s", subject)
        return False

    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.error(
            "Email delivery failed | subject=%s | recipients=%s | error=%s",
            subject,
            ",".join(recipient_list),
            exc,
        )
        if settings.DEBUG:
            raise
        return False


def _get_admin_notification_recipients():
    recipients = list(getattr(settings, 'ORDER_ALERT_EMAILS', []))
    if recipients:
        return recipients

    admins = getattr(settings, 'ADMINS', [])
    return [email for _name, email in admins if email]


def _get_customer_recipients(order):
    recipients = []

    if getattr(order, 'email', ''):
        recipients.append(order.email)
    user_email = getattr(getattr(order, 'user', None), 'email', '')
    if user_email:
        recipients.append(user_email)

    deduped_recipients = []
    seen = set()
    for recipient in recipients:
        normalized = (recipient or '').strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_recipients.append(recipient.strip())

    return deduped_recipients


def _get_notification_fields(email_type):
    if email_type == 'confirmation':
        return 'confirmation_email_sent', 'confirmation_email_claimed_at', send_order_confirmation_email
    if email_type == 'payment':
        return 'payment_email_sent', 'payment_email_claimed_at', send_payment_confirmation_email
    if email_type == 'admin':
        return 'admin_notification_sent', 'admin_notification_claimed_at', send_admin_new_order_alert_email
    raise ValueError(f'Unsupported notification type: {email_type}')


def send_order_confirmation_email(order):
    """Send the order confirmation email to the customer."""
    try:
        recipients = _get_customer_recipients(order)
        if not recipients:
            logger.warning("Cannot send confirmation email | order_id=%s | no email address", order.id)
            return False

        sent = _send_html_email(
            subject=f'Order Confirmation - Order #{order.id}',
            template_name='emails/order_confirmation.html',
            context=_build_order_email_context(order),
            recipient_list=recipients,
        )
        if not sent:
            return False

        logger.info("Order confirmation email sent | order_id=%s | user_id=%s", order.id, order.user_id)
        return True

    except Exception as exc:
        logger.error("Failed to send order confirmation email | order_id=%s | error=%s", order.id, exc)
        return False


def send_payment_confirmation_email(order):
    """Send the payment confirmation email to the customer."""
    try:
        recipients = _get_customer_recipients(order)
        if not recipients:
            logger.warning("Cannot send payment email | order_id=%s | no email address", order.id)
            return False

        sent = _send_html_email(
            subject=f'Payment Confirmed - Order #{order.id}',
            template_name='emails/payment_confirmation.html',
            context=_build_order_email_context(
                order,
                razorpay_payment_id=order.razorpay_payment_id,
                total_price=order.total_price,
            ),
            recipient_list=recipients,
        )
        if not sent:
            return False

        logger.info("Payment confirmation email sent | order_id=%s | user_id=%s", order.id, order.user_id)
        return True

    except Exception as exc:
        logger.error("Failed to send payment confirmation email | order_id=%s | error=%s", order.id, exc)
        return False


def send_order_status_update_email(order, status):
    """Send an order status update email to the customer."""
    try:
        recipients = _get_customer_recipients(order)
        if not recipients:
            logger.warning("Cannot send status email | order_id=%s | no email address", order.id)
            return False

        status_messages = {
            'paid': 'Your payment has been received and your order is now marked as paid.',
            'packed': 'Your order has been packed and is getting ready for shipment.',
            'confirmed': 'Your order has been confirmed and is being prepared.',
            'processing': 'Your order is being processed and will be shipped soon.',
            'shipped': 'Your order has been shipped and is on its way.',
            'delivered': 'Your order has been delivered successfully.',
            'cancelled': 'Your order has been cancelled.',
        }
        sent = _send_html_email(
            subject=f'Order Update - Order #{order.id} is {order.get_status_display()}',
            template_name='emails/order_status_update.html',
            context=_build_order_email_context(
                order,
                status_message=status_messages.get(status, f'Status updated to {order.get_status_display()}.'),
                status=status,
            ),
            recipient_list=recipients,
        )
        if not sent:
            return False

        logger.info(
            "Order status update email sent | order_id=%s | user_id=%s | status=%s",
            order.id,
            order.user_id,
            status,
        )
        return True

    except Exception as exc:
        logger.error(
            "Failed to send status update email | order_id=%s | status=%s | error=%s",
            order.id,
            status,
            exc,
        )
        return False


def send_admin_new_order_alert_email(order):
    """Send the new paid-order alert email to store admins."""
    recipients = _get_admin_notification_recipients()
    if not recipients:
        logger.warning("Skipping admin order alert because ORDER_ALERT_EMAILS/ADMINS is empty | order_id=%s", order.id)
        return False

    try:
        sent = _send_html_email(
            subject=f'New Paid Order - #{order.id} - SYAFRA',
            template_name='emails/admin_new_order_alert.html',
            context=_build_order_email_context(order),
            recipient_list=recipients,
        )
        if not sent:
            return False

        logger.info("Admin order alert email sent | order_id=%s | recipients=%s", order.id, ",".join(recipients))
        return True
    except Exception as exc:
        logger.error("Failed to send admin order alert email | order_id=%s | error=%s", order.id, exc)
        return False


def _claim_notification_email(order_id, email_type):
    from orders.models import Order

    sent_field, claim_field, _sender = _get_notification_fields(email_type)
    claim_started_at = timezone.now()
    expires_before = claim_started_at - _get_email_claim_timeout()
    claim_filter = (
        Q(**{f'{claim_field}__isnull': True})
        | Q(**{f'{claim_field}__lt': expires_before})
    )
    claimed = (
        Order.objects.filter(pk=order_id, **{sent_field: False})
        .filter(claim_filter)
        .update(**{claim_field: claim_started_at})
    )
    if not claimed and FORCE_EMAIL_RETRY:
        order_obj = Order.objects.filter(pk=order_id).first()
        if order_obj:
            existing_claimed_at = getattr(order_obj, claim_field, None)
            if existing_claimed_at is not None:
                claim_age = claim_started_at - existing_claimed_at
                if claim_age >= _get_email_claim_timeout():
                    logger.warning(f"FORCE RESET: Stale claim detected for order {order_id}, {email_type} email (age: {claim_age})")
                    Order.objects.filter(pk=order_id).update(**{claim_field: None})
                    expires_before = timezone.now() - _get_email_claim_timeout()
                    claim_filter = (
                        Q(**{f'{claim_field}__isnull': True})
                        | Q(**{f'{claim_field}__lt': expires_before})
                    )
                    claimed = (
                        Order.objects.filter(pk=order_id, **{sent_field: False})
                        .filter(claim_filter)
                        .update(**{claim_field: claim_started_at})
                    )
    if not claimed:
        return None, None

    order = (
        Order.objects.select_related('user')
        .prefetch_related('items__product')
        .get(pk=order_id)
    )
    return order, claim_started_at


def _release_notification_email_claim(order_id, email_type, claim_started_at):
    from orders.models import Order

    _sent_field, claim_field, _sender = _get_notification_fields(email_type)
    Order.objects.filter(pk=order_id, **{claim_field: claim_started_at}).update(**{claim_field: None})


def _complete_notification_email_claim(order_id, email_type, claim_started_at):
    from orders.models import Order

    sent_field, claim_field, _sender = _get_notification_fields(email_type)
    return (
        Order.objects.filter(pk=order_id, **{claim_field: claim_started_at, sent_field: False})
        .update(**{sent_field: True, claim_field: None})
    )


def _notification_claim_is_current(order_id, email_type, claim_started_at):
    from orders.models import Order

    sent_field, claim_field, _sender = _get_notification_fields(email_type)
    return Order.objects.filter(
        pk=order_id,
        **{claim_field: claim_started_at, sent_field: False},
    ).exists()


def send_notification_email(order_id, email_type, status=None, raise_on_failure=False):
    """
    Send an email notification synchronously without delay.

    Status emails: DIRECT SEND - no claim system, instant delivery
    Confirmation/payment emails: Use claim-based idempotency
    """
    from orders.models import Order

    logger.info(f"EMAIL SEND START | type={email_type} | order={order_id} | raise_on_failure={raise_on_failure}")

    if email_type == 'status':
        logger.info(f"🔥 STATUS EMAIL - DIRECT SEND (NO CLAIM) | order={order_id} | status={status}")
        
        try:
            order = Order.objects.select_related('user').get(pk=order_id)
        except Order.DoesNotExist:
            logger.warning("Skipping status email for missing order %s", order_id)
            return False

        try:
            sent = send_order_status_update_email(order, status or order.status)
            if sent:
                logger.info(f"✅ STATUS EMAIL SENT INSTANTLY | order={order_id} | status={status}")
                return True
            logger.error(f"❌ STATUS EMAIL FAILED | order={order_id} | status={status}")
            if raise_on_failure:
                raise EmailDeliveryError(f"Status email failed for order {order_id}")
            return False
        except Exception as exc:
            logger.error(f"❌ STATUS EMAIL ERROR | order={order_id} | error={exc}")
            if raise_on_failure:
                raise
            return False

    if email_type in {'confirmation', 'payment', 'admin'}:
        _sent_field, _claim_field, sender = _get_notification_fields(email_type)

        try:
            order, claim_started_at = _claim_notification_email(order_id, email_type)
        except Order.DoesNotExist:
            logger.warning("Skipping %s email for missing order %s", email_type, order_id)
            return False

        if not order:
            logger.warning(f"EMAIL CLAIM BLOCKED for order {order_id}, {email_type}")
            
            if FORCE_EMAIL_RETRY:
                order_obj = Order.objects.filter(pk=order_id).first()
                if order_obj:
                    existing_claimed_at = getattr(order_obj, _claim_field, None)
                    if existing_claimed_at is not None:
                        claim_age = timezone.now() - existing_claimed_at
                        if claim_age >= _get_email_claim_timeout():
                            logger.warning(f"RESETTING STALE EMAIL CLAIM for order {order_id}, {email_type} (age: {claim_age})")
                            Order.objects.filter(pk=order_id).update(**{_claim_field: None})
                            
                            try:
                                order, claim_started_at = _claim_notification_email(order_id, email_type)
                                logger.info(f"RETRY AFTER STALE CLAIM RESET SUCCESS | order={order_id}, {email_type}")
                            except Order.DoesNotExist:
                                logger.warning("Skipping %s email for missing order %s after reset", email_type, order_id)
                                return False
            
            if not order:
                if Order.objects.filter(pk=order_id).exists():
                    logger.info("Skipping duplicate or in-flight %s email for order %s", email_type, order_id)
                else:
                    logger.warning("Skipping %s email for missing order %s", email_type, order_id)
                return False

        logger.info(f"EMAIL CLAIMED | order={order_id}, claimed_at={claim_started_at}, type={email_type}")

        try:
            if not _notification_claim_is_current(order.id, email_type, claim_started_at):
                logger.info(
                    "Skipping %s email because claim is no longer current | order_id=%s",
                    email_type,
                    order.id,
                )
                return False
            
            logger.info(f"EMAIL SENDING NOW | type={email_type} | order={order_id}")
            sent = sender(order)
            
            if not sent:
                raise EmailDeliveryError(f"{email_type} email returned False for order {order.id}")
            
            _complete_notification_email_claim(order.id, email_type, claim_started_at)
            logger.info(f"EMAIL SENT SUCCESS | type={email_type} | order={order_id} | sent={sent}")
            return True
        except Exception as exc:
            _release_notification_email_claim(order.id, email_type, claim_started_at)
            logger.error(f"EMAIL SEND FAILED | type={email_type} | order={order_id} | error={exc}")
            if raise_on_failure:
                if isinstance(exc, EmailDeliveryError):
                    raise
                raise EmailDeliveryError(
                    f"Failed to send {email_type} email for order {order.id}"
                ) from exc
            logger.warning(
                "Released %s email claim after send failure | order_id=%s | error=%s",
                email_type,
                order.id,
                exc,
            )
            return False

    logger.warning("Unknown email notification type %s for order %s", email_type, order_id)
    return False
