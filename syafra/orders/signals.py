import logging

from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from syafra.logging_context import get_correlation_id

from .models import Order, OrderItem

logger = logging.getLogger(__name__)


def _dispatch_whatsapp_notification(order_pk, status, correlation_id=None):
    try:
        from .tasks import send_whatsapp_notification
    except ImportError:
        logger.warning("Celery not available, skipping async WhatsApp notification for order %s", order_pk)
        return

    try:
        send_whatsapp_notification.delay(order_pk, status, correlation_id=correlation_id)
    except Exception as exc:
        logger.exception(
            "Failed to queue WhatsApp notification for order %s with status %s: %s",
            order_pk,
            status,
            exc,
        )


def queue_whatsapp_notification(order, status):
    try:
        correlation_id = get_correlation_id()
        _dispatch_whatsapp_notification(
            order.pk,
            status,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        logger.exception(
            "Failed to register WhatsApp notification for order %s with status %s: %s",
            order.pk,
            status,
            exc,
        )


def queue_email_notification(order, email_type, status_override=None):
    """Send order notification emails immediately without interrupting order saves."""
    try:
        correlation_id = get_correlation_id()

        from .services.email_service import _get_notification_fields

        if email_type in ("confirmation", "payment", "admin"):
            sent_field, _, _ = _get_notification_fields(email_type)
            if Order.objects.filter(pk=order.pk).values_list(sent_field, flat=True).first():
                logger.info("Email already sent | type=%s | order=%s | skipping", email_type, order.pk)
                return

        _send_email_instant(
            order.pk,
            email_type,
            status_override,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        logger.exception(
            "Failed to send immediate email notification | order_id=%s | type=%s | error=%s",
            order.id,
            email_type,
            exc,
        )


def _send_email_instant(order_pk, email_type, status_override=None, correlation_id=None):
    """Send email via the synchronous path for checkout-critical notifications."""
    from syafra.logging_context import correlation_id_context
    from .services.email_service import EmailDeliveryError, send_notification_email

    with correlation_id_context(correlation_id):
        logger.info(
            "Email send started | type=%s | order=%s | correlation_id=%s",
            email_type,
            order_pk,
            correlation_id,
        )

        if email_type in ["confirmation", "status"]:
            logger.info("Critical email forced to sync path | type=%s | order=%s", email_type, order_pk)

        try:
            sent = send_notification_email(
                order_pk,
                email_type,
                status=status_override,
                raise_on_failure=True,
            )
            logger.info("Email send success | type=%s | order=%s | sent=%s", email_type, order_pk, sent)
        except EmailDeliveryError as exc:
            logger.warning("Email delivery failed for order %s: %s", order_pk, exc)
        except Exception as exc:
            logger.exception("Failed to send instant email for order %s: %s", order_pk, exc)


@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    try:
        order = instance.order
        total = order.items.aggregate(
            total=Coalesce(
                Sum(
                    F("price") * F("quantity"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )["total"]
        Order.objects.filter(pk=order.pk).update(total_price=total)
        logger.debug("Order total updated | Order #%s | New total: %s", order.id, total)
    except Exception as exc:
        logger.error("Error updating order total for item %s: %s", instance.id, exc)
