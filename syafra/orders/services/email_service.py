"""
Production-safe email helpers.
"""
import logging
from datetime import timedelta

from accounts.utils.email import send_email
from accounts.email_tracking import latest_retryable_failure
from accounts.models import EmailLog
from django.conf import settings
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import escape, strip_tags

logger = logging.getLogger(__name__)

FORCE_EMAIL_RETRY = getattr(settings, 'FORCE_EMAIL_RETRY', False)
ORDER_EVENT_CREATED = 'created'
ORDER_EVENT_CONFIRMED = 'confirmed'
ORDER_EVENT_SHIPPED = 'shipped'
ORDER_EVENT_DELIVERED = 'delivered'
ORDER_EVENT_CANCELLED = 'cancelled'
ORDER_EMAIL_STATUS_EVENT_MAP = {
    'paid': ORDER_EVENT_CONFIRMED,
    'packed': ORDER_EVENT_CONFIRMED,
    'confirmed': ORDER_EVENT_CONFIRMED,
    'shipped': ORDER_EVENT_SHIPPED,
    'delivered': ORDER_EVENT_DELIVERED,
    'cancelled': ORDER_EVENT_CANCELLED,
}
NON_FAILED_EMAIL_LOG_STATUSES = [
    EmailLog.STATUS_QUEUED,
    EmailLog.STATUS_ACCEPTED,
    EmailLog.STATUS_DELIVERED,
    EmailLog.STATUS_DEFERRED,
    EmailLog.STATUS_DROPPED,
    EmailLog.STATUS_BOUNCED,
    EmailLog.STATUS_BLOCKED,
    EmailLog.STATUS_OPENED,
    EmailLog.STATUS_SPAM_REPORTED,
]
ORDER_EMAIL_EVENT_CONFIG = {
    ORDER_EVENT_CREATED: {
        'email_type': EmailLog.TYPE_ORDER_CONFIRMATION,
        'subject': 'Order Created - Order #{order_id}',
        'headline': 'Your Order Has Been Created',
        'status_label': 'Created',
        'message': 'We have created your order and will confirm the next fulfillment step shortly.',
    },
    ORDER_EVENT_CONFIRMED: {
        'email_type': EmailLog.TYPE_ORDER_STATUS,
        'subject': 'Order Confirmed - Order #{order_id}',
        'headline': 'Your Order Is Confirmed',
        'status_label': 'Confirmed',
        'message': 'Your order has been confirmed and is now being prepared.',
    },
    ORDER_EVENT_SHIPPED: {
        'email_type': EmailLog.TYPE_ORDER_STATUS,
        'subject': 'Order Shipped - Order #{order_id}',
        'headline': 'Your Order Is On The Way',
        'status_label': 'Shipped',
        'message': 'Your order has been shipped.',
    },
    ORDER_EVENT_DELIVERED: {
        'email_type': EmailLog.TYPE_ORDER_STATUS,
        'subject': 'Order Delivered - Order #{order_id}',
        'headline': 'Your Order Has Been Delivered',
        'status_label': 'Delivered',
        'message': 'Your order has been delivered successfully.',
    },
    ORDER_EVENT_CANCELLED: {
        'email_type': EmailLog.TYPE_ORDER_STATUS,
        'subject': 'Order Cancelled - Order #{order_id}',
        'headline': 'Your Order Has Been Cancelled',
        'status_label': 'Cancelled',
        'message': 'Your order has been cancelled. If you have any questions, please contact support.',
    },
}


class EmailDeliveryError(Exception):
    """Raised when an email send should be retried."""

    def __init__(self, message, *, retryable=True):
        super().__init__(message)
        self.retryable = retryable


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


def get_order_status_email_event(status):
    return ORDER_EMAIL_STATUS_EVENT_MAP.get((status or '').strip().lower())


def _normalize_order_event_type(event_type):
    return (event_type or '').strip().lower()


def _order_event_config(event_type):
    return ORDER_EMAIL_EVENT_CONFIG.get(_normalize_order_event_type(event_type))


def _order_event_already_logged(order, event_type):
    if not getattr(order, 'pk', None):
        return False

    return EmailLog.objects.filter(
        order=order,
        correlation_id=str(order.pk),
        event_type=_normalize_order_event_type(event_type),
    ).exists()


def _build_order_event_context(order, event_type):
    event_type = _normalize_order_event_type(event_type)
    config = _order_event_config(event_type)
    tracking_id = (getattr(order, 'tracking_id', '') or '').strip()
    status_message = config['message']
    if event_type == ORDER_EVENT_SHIPPED:
        if tracking_id:
            status_message = f"{status_message} Your tracking ID is {tracking_id}."
        else:
            status_message = f"{status_message} Tracking details will be shared as soon as they are available."

    return {
        'order': order,
        'event_type': event_type,
        'headline': config['headline'],
        'currency': get_currency_symbol(),
        'customer_name': order.customer_name or getattr(getattr(order, 'user', None), 'get_full_name', lambda: '')() or 'Customer',
        'order_status_label': config['status_label'],
        'status_message': status_message,
        'tracking_id': tracking_id,
        'show_tracking_id': bool(tracking_id and event_type == ORDER_EVENT_SHIPPED),
    }


def _build_fast_order_event_messages(context):
    order = context['order']
    tracking_line = f"\nTracking ID: {context['tracking_id']}" if context['show_tracking_id'] else ""
    plain_message = (
        f"{context['headline']}\n\n"
        f"Hello {context['customer_name']},\n\n"
        f"{context['status_message']}\n\n"
        f"Order ID: #{order.id}\n"
        f"Current Status: {context['order_status_label']}\n"
        f"Order Total: {context['currency']}{order.total_price:.2f}"
        f"{tracking_line}\n\n"
        f"Shipping Address:\n{order.shipping_address}\n\n"
        "If you need help, reply to this email and our team will assist you."
    )

    tracking_html = ""
    if context['show_tracking_id']:
        tracking_html = (
            '<tr><td style="padding:8px 0;color:#6b7280;">Tracking ID</td>'
            f'<td style="padding:8px 0;text-align:right;"><strong>{escape(context["tracking_id"])}</strong></td></tr>'
        )

    html_message = f"""
<!DOCTYPE html>
<html lang="en">
<body style="font-family: Arial, sans-serif; color: #333333; background: #f5f5f5; margin: 0; padding: 24px;">
    <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e5e7eb; padding: 28px;">
        <h1 style="font-size: 24px; margin: 0 0 16px;">{escape(context['headline'])}</h1>
        <p style="margin: 0 0 12px;">Hello {escape(context['customer_name'])},</p>
        <p style="margin: 0 0 18px;">{escape(context['status_message'])}</p>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 18px;">
            <tbody>
                <tr><td style="padding:8px 0;color:#6b7280;">Order ID</td><td style="padding:8px 0;text-align:right;"><strong>#{order.id}</strong></td></tr>
                <tr><td style="padding:8px 0;color:#6b7280;">Current Status</td><td style="padding:8px 0;text-align:right;"><strong>{escape(context['order_status_label'])}</strong></td></tr>
                <tr><td style="padding:8px 0;color:#6b7280;">Order Total</td><td style="padding:8px 0;text-align:right;"><strong>{escape(context['currency'])}{order.total_price:.2f}</strong></td></tr>
                {tracking_html}
            </tbody>
        </table>
        <p style="margin: 0 0 8px;">Shipping Address:</p>
        <div style="padding: 12px; border: 1px solid #e5e7eb; background: #f9fafb; white-space: pre-wrap; margin-bottom: 18px;">{escape(order.shipping_address)}</div>
        <p style="margin: 0; color: #6b7280; font-size: 13px;">If you need help, reply to this email and our team will assist you.</p>
    </div>
</body>
</html>
""".strip()

    return html_message, plain_message


def send_order_email(order, event_type):
    """
    Send an immediate, idempotent customer email for a specific order event.
    """
    print("EMAIL TRIGGERED")
    event_type = _normalize_order_event_type(event_type)
    config = _order_event_config(event_type)
    if config is None:
        logger.warning("Skipping order email because event_type is unsupported | order_id=%s | event_type=%s", getattr(order, 'pk', None), event_type)
        return False

    recipients = _get_customer_recipients(order)
    if not recipients:
        logger.warning("Skipping order email because the order has no customer recipients | order_id=%s | event_type=%s", order.id, event_type)
        return False

    if _order_event_already_logged(order, event_type):
        logger.info("Skipping duplicate order event email | order_id=%s | event_type=%s", order.id, event_type)
        return False

    context = _build_order_event_context(order, event_type)
    subject = config['subject'].format(order_id=order.id)
    html_message, plain_message = _build_fast_order_event_messages(context)
    tracking_id = context['tracking_id']

    try:
        sent = send_email(
            subject=subject,
            message=plain_message,
            recipient_list=recipients,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            email_type=config['email_type'],
            event_type=event_type,
            user=getattr(order, 'user', None),
            order=order,
            correlation_id=str(order.id),
            metadata={
                'flow': 'instant_order_event_email',
                'event_type': event_type,
                'order_status': order.status,
                'tracking_id': tracking_id,
                'template_name': 'inline_order_event',
            },
            max_retries=1,
        )
    except Exception as exc:
        logger.exception("Order event email raised an exception | order_id=%s | event_type=%s | error=%s", order.id, event_type, exc)
        return False

    if not sent:
        logger.error("Order event email failed | order_id=%s | event_type=%s | recipients=%s", order.id, event_type, ",".join(recipients))
        return False

    logger.info("Order event email sent | order_id=%s | event_type=%s | recipients=%s", order.id, event_type, ",".join(recipients))
    return True


def send_order_status_email_if_changed(order, old_status, new_status):
    """
    Send a customer-facing status email directly from the action that changed it.
    """
    old_status = (old_status or '').strip().lower()
    new_status = (new_status or '').strip().lower()
    if old_status == new_status:
        logger.info("Skipping status email because status did not change | order_id=%s | status=%s", order.id, new_status)
        return False

    event_type = get_order_status_email_event(new_status)
    if not event_type:
        logger.info(
            "Skipping status email because status has no customer email event | order_id=%s | old_status=%s | new_status=%s",
            order.id,
            old_status or "-",
            new_status or "-",
        )
        return False

    return send_order_email(order, event_type)


def _email_log_type_for_notification(email_type):
    mapping = {
        'confirmation': EmailLog.TYPE_ORDER_CONFIRMATION,
        'payment': EmailLog.TYPE_PAYMENT_CONFIRMATION,
        'status': EmailLog.TYPE_ORDER_STATUS,
        'admin': EmailLog.TYPE_ADMIN_ORDER_ALERT,
    }
    return mapping.get(email_type, EmailLog.TYPE_GENERIC)


def _send_html_email(*, subject, template_name, context, recipient_list, email_type, order):
    if not recipient_list:
        logger.warning("Skipping email because no recipients were provided | subject=%s", subject)
        return False

    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)

    try:
        sent = send_email(
            subject=subject,
            message=plain_message,
            recipient_list=recipient_list,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            email_type=_email_log_type_for_notification(email_type),
            user=getattr(order, 'user', None),
            order=order,
            metadata={
                'flow': 'order_notification',
                'template_name': template_name,
            },
        )
        return bool(sent)
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


def _get_order_event_recipients(order):
    if getattr(order, 'email', ''):
        return [order.email.strip()]
    user_email = getattr(getattr(order, 'user', None), 'email', '')
    if user_email:
        return [user_email.strip()]
    return []


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
        recipients = _get_order_event_recipients(order)
        if not recipients:
            logger.warning("Cannot send confirmation email | order_id=%s | no email address", order.id)
            return False

        sent = _send_html_email(
            subject=f'Order Confirmation - Order #{order.id}',
            template_name='emails/order_confirmation.html',
            context=_build_order_email_context(order),
            recipient_list=recipients,
            email_type='confirmation',
            order=order,
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
            email_type='payment',
            order=order,
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
    mapped_event = get_order_status_email_event(status)
    if mapped_event:
        return send_order_email(order, mapped_event)

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
            email_type='status',
            order=order,
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
            email_type='admin',
            order=order,
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
                retryable = latest_retryable_failure(
                    order,
                    _email_log_type_for_notification(email_type),
                ) is not None
                raise EmailDeliveryError(
                    f"{email_type} email returned False for order {order.id}",
                    retryable=retryable,
                )
            
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
                    f"Failed to send {email_type} email for order {order.id}",
                    retryable=False,
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
