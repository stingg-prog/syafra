import logging

from django.conf import settings
from django.db import transaction
from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save, pre_save
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


def _dispatch_email_notification(order_pk, email_type, status_override=None, correlation_id=None):
    try:
        from .tasks import send_email_sync

        send_email_sync(order_pk, email_type, status=status_override, correlation_id=correlation_id)
    except Exception as exc:
        logger.exception("Failed to send email notification for order %s: %s", order_pk, exc)


def _schedule_on_commit_once(kind, identifier, callback):
    connection = transaction.get_connection()

    key = (kind, identifier)
    for queued_callback in getattr(connection, 'run_on_commit', []):
        queued_func = queued_callback[1]
        if getattr(queued_func, '_orders_on_commit_key', None) == key:
            logger.debug("Skipping duplicate on-commit registration for %s", key)
            return False

    def run_once():
        callback()

    run_once._orders_on_commit_key = key
    transaction.on_commit(run_once)
    return True


def _enqueue_async_email_notification(order_pk, email_type, status_override=None, correlation_id=None):
    return False


def queue_whatsapp_notification(order, status):
    try:
        correlation_id = get_correlation_id()
        _schedule_on_commit_once(
            'whatsapp',
            (order.pk, status),
            lambda order_pk=order.pk, status=status, correlation_id=correlation_id: _dispatch_whatsapp_notification(
                order_pk,
                status,
                correlation_id=correlation_id,
            ),
        )
    except Exception as exc:
        logger.exception(
            "Failed to register WhatsApp notification for order %s with status %s: %s",
            order.pk,
            status,
            exc,
        )


def queue_email_notification(order, email_type, status_override=None):
    try:
        correlation_id = get_correlation_id()
        
        use_instant = getattr(settings, 'ORDER_INSTANT_EMAIL_ENABLED', True)
        
        if use_instant:
            _send_email_instant(
                order.pk,
                email_type,
                status_override,
                correlation_id=correlation_id,
            )
        else:
            _send_email_notification_with_fallback(
                order.pk,
                email_type,
                status_override,
                correlation_id=correlation_id,
            )
    except Exception as exc:
        logger.error("Failed to queue email notification for order %s: %s", order.id, exc)


def _send_email_notification_with_fallback(order_pk, email_type, status_override=None, correlation_id=None):
    try:
        sent_async = _enqueue_async_email_notification(order_pk, email_type, status_override, correlation_id=correlation_id)
        logger.info(f"Email async queued: {sent_async} for order {order_pk}")
        
        if not sent_async:
            try:
                _dispatch_email_notification(order_pk, email_type, status_override, correlation_id=correlation_id)
            except Exception:
                logger.exception(f"Fallback email send failed for order {order_pk}")
    except Exception:
        logger.exception(f"Email notification failed completely for order {order_pk}, attempting sync fallback")
        try:
            _dispatch_email_notification(order_pk, email_type, status_override, correlation_id=correlation_id)
        except Exception:
            logger.exception(f"Emergency fallback email send failed for order {order_pk}")


def _send_email_instant(order_pk, email_type, status_override=None, correlation_id=None):
    """Send email INSTANTLY via sync dispatch - no async delay, no retries for speed."""
    from syafra.logging_context import correlation_id_context
    from .services.email_service import EmailDeliveryError, send_notification_email
    
    with correlation_id_context(correlation_id):
        logger.info(f"EMAIL SENT INSTANTLY | type={email_type} | order={order_pk} | correlation_id={correlation_id}")
        
        if email_type in ['confirmation', 'status']:
            logger.info(f"CRITICAL EMAIL - FORCE SYNC | type={email_type} | order={order_pk}")
        
        try:
            sent = send_notification_email(
                order_pk,
                email_type,
                status=status_override,
                raise_on_failure=True,
            )
            
            logger.info(f"EMAIL SENT SUCCESS | type={email_type} | order={order_pk} | sent={sent}")
            
        except EmailDeliveryError as exc:
            logger.warning(f"Email delivery failed for order {order_pk}: {exc}")
            logger.info(f"RETRYING SYNC | type={email_type} | order={order_pk}")
            try:
                sent = send_notification_email(
                    order_pk,
                    email_type,
                    status=status_override,
                    raise_on_failure=True,
                )
                logger.info(f"EMAIL RETRY SUCCESS | type={email_type} | order={order_pk} | sent={sent}")
            except Exception as retry_exc:
                logger.error(f"EMAIL RETRY FAILED | type={email_type} | order={order_pk}: {retry_exc}")
                raise
        except Exception as exc:
            logger.exception(f"Failed to send instant email for order {order_pk}: {exc}")
            raise


@receiver(pre_save, sender=Order)
def track_order_changes(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            instance._previous_status = old_instance.status
            instance._previous_payment_status = old_instance.payment_status
            instance._previous_total = old_instance.total_price
        except Order.DoesNotExist:
            instance._previous_status = None
            instance._previous_payment_status = None
            instance._previous_total = None
    else:
        instance._previous_status = None
        instance._previous_payment_status = None
        instance._previous_total = None


@receiver(post_save, sender=Order)
def handle_order_notifications(sender, instance, created, **kwargs):
    if created:
        logger.info("New order created | Order #%s | User: %s", instance.id, instance.user.id)

        if instance.status == 'confirmed' and instance.payment_status == 'paid':
            logger.info(f"🔥 PAYMENT DETECTED (created) → order={instance.id}, status={instance.status}, payment={instance.payment_status}")
            try:
                from .services.order_service import ensure_paid_order_stock_reduced
                if not instance.stock_reduced:
                    ensure_paid_order_stock_reduced(instance)
            except Exception as exc:
                logger.warning(
                    "Could not reduce stock from signal for order #%s (admin may handle it): %s",
                    instance.id,
                    exc,
                )
            queue_email_notification(instance, 'confirmation')
            queue_email_notification(instance, 'payment')
            queue_whatsapp_notification(instance, 'created')
            logger.info("🔥 EMAILS TRIGGERED for new paid order #%s", instance.id)
        return

    if not hasattr(instance, '_previous_status'):
        instance._previous_status = None
        instance._previous_payment_status = None

    old_status = instance._previous_status
    new_status = instance.status
    prev_pay = getattr(instance, '_previous_payment_status', None)

    if old_status is None:
        if hasattr(instance, '_admin_old_status'):
            old_status = instance._admin_old_status
            prev_pay = getattr(instance, '_admin_old_payment_status', None)
        else:
            try:
                old_order = Order.objects.get(pk=instance.pk)
                old_status = old_order.status
                prev_pay = old_order.payment_status
            except Order.DoesNotExist:
                old_status = None
                prev_pay = None

    logger.info("Status check | Order #%s | old_status=%s, new_status=%s | old_pay=%s, new_pay=%s", 
                 instance.id, old_status, new_status, prev_pay, instance.payment_status)

    if old_status == new_status and prev_pay == instance.payment_status:
        logger.info("No status change for order #%s, skipping notifications", instance.id)
        return

    logger.info("🔥 STATUS CHANGE DETECTED | Order #%s | %s→%s, pay:%s→%s", 
                 instance.id, old_status, new_status, prev_pay, instance.payment_status)

    if instance.status == 'confirmed' and instance.payment_status == 'paid':
        logger.info(f"🔥 PAYMENT CONFIRMED TRIGGER → order={instance.id}")
        try:
            from .services.order_service import ensure_paid_order_stock_reduced
            if not instance.stock_reduced:
                ensure_paid_order_stock_reduced(instance)
        except Exception as exc:
            logger.warning(
                "Could not reduce stock from signal for order #%s (admin may handle it): %s",
                instance.id,
                exc,
            )
        queue_email_notification(instance, 'confirmation')
        queue_email_notification(instance, 'payment')
        queue_whatsapp_notification(instance, 'created')
        logger.info("🔥 EMAILS TRIGGERED for paid order #%s", instance.id)
        return

    if new_status == 'confirmed':
        queue_email_notification(instance, 'status', status_override='confirmed')
        queue_whatsapp_notification(instance, 'processing')
        logger.info("Confirmed notifications queued for order #%s", instance.id)
    elif new_status == 'processing':
        queue_email_notification(instance, 'status', status_override='processing')
        queue_whatsapp_notification(instance, 'processing')
        logger.info("Processing notifications queued for order #%s", instance.id)
    elif new_status == 'shipped':
        queue_email_notification(instance, 'status', status_override='shipped')
        queue_whatsapp_notification(instance, 'shipped')
        logger.info("Shipped notifications queued for order #%s", instance.id)
    elif new_status == 'delivered':
        queue_email_notification(instance, 'status', status_override='delivered')
        queue_whatsapp_notification(instance, 'delivered')
        logger.info("Delivered notifications queued for order #%s", instance.id)


@receiver([post_save, post_delete], sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    try:
        order = instance.order
        total = order.items.aggregate(
            total=Coalesce(
                Sum(
                    F('price') * F('quantity'),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                ),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )['total']
        Order.objects.filter(pk=order.pk).update(total_price=total)
        logger.debug("Order total updated | Order #%s | New total: %s", order.id, total)
    except Exception as exc:
        logger.error("Error updating order total for item %s: %s", instance.id, exc)
