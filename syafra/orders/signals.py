import logging

from django.db import transaction
from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from syafra.logging_context import get_correlation_id

from .models import Order, OrderItem, WhatsAppSettings, PaymentSettings
from .utils import calculate_delivery_charge

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=WhatsAppSettings)
def clear_whatsapp_cache(sender, **kwargs):
    from django.core.cache import cache
    from .models import WHATSAPP_SETTINGS_CACHE_KEY
    cache.delete(WHATSAPP_SETTINGS_CACHE_KEY)


@receiver([post_save, post_delete], sender=PaymentSettings)
def clear_payment_cache(sender, **kwargs):
    from django.core.cache import cache
    from .models import PAYMENT_SETTINGS_CACHE_KEY
    cache.delete(PAYMENT_SETTINGS_CACHE_KEY)
    cache.delete(f'{PAYMENT_SETTINGS_CACHE_KEY}_none')


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
    """Send order notification emails immediately after the DB transaction commits."""
    try:
        correlation_id = get_correlation_id()

        from .services.email_service import _get_notification_fields

        if email_type in ("confirmation", "payment", "admin"):
            sent_field, _, _ = _get_notification_fields(email_type)
            if Order.objects.filter(pk=order.pk).values_list(sent_field, flat=True).first():
                logger.info("Email already sent | type=%s | order=%s | skipping", email_type, order.pk)
                return

        transaction.on_commit(
            lambda pk=order.pk, et=email_type, so=status_override, cid=correlation_id:
            _send_email_on_commit(pk, et, so, cid)
        )
    except Exception as exc:
        logger.exception(
            "Failed to schedule email notification | order_id=%s | type=%s | error=%s",
            order.id,
            email_type,
            exc,
        )


def _send_email_on_commit(order_pk, email_type, status_override, correlation_id):
    from syafra.logging_context import correlation_id_context
    from .services.email_service import EmailDeliveryError, send_notification_email

    with correlation_id_context(correlation_id):
        logger.info(
            "Email send on_commit | type=%s | order=%s | correlation_id=%s",
            email_type, order_pk, correlation_id,
        )
        try:
            sent = send_notification_email(order_pk, email_type, status=status_override, raise_on_failure=False)
            logger.info(
                "Email send result | type=%s | order=%s | sent=%s",
                email_type, order_pk, sent,
            )
        except Exception as exc:
            logger.exception(
                "Email send failed | type=%s | order=%s | error=%s",
                email_type, order_pk, exc,
            )


@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    try:
        order = instance.order
        result = order.items.aggregate(
            total=Coalesce(
                Sum(
                    F("price") * F("quantity"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
            qty=Coalesce(
                Sum("quantity", output_field=DecimalField(max_digits=10, decimal_places=0)),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=0),
            ),
        )
        items_total = result["total"]
        total_qty = int(result["qty"])
        delivery_charge = calculate_delivery_charge(total_qty)
        final_total = items_total + delivery_charge
        Order.objects.filter(pk=order.pk).update(total_price=final_total, delivery_charge=delivery_charge)
        logger.debug("Order total updated | Order #%s | Items: %s | Delivery: %s | Total: %s", order.id, items_total, delivery_charge, final_total)
    except Exception as exc:
        logger.error("Error updating order total for item %s: %s", instance.id, exc)
