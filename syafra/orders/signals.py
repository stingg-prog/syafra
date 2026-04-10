import logging

from django.conf import settings
from django.db import transaction
from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from syafra.logging_context import get_correlation_id

from .models import Order, OrderItem, PAID_FULFILLMENT_STATUSES

logger = logging.getLogger(__name__)


def _is_paid_fulfillment_stage(status, payment_status):
    return payment_status == "paid" and status in PAID_FULFILLMENT_STATUSES


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
    for queued_callback in getattr(connection, "run_on_commit", []):
        queued_func = queued_callback[1]
        if getattr(queued_func, "_orders_on_commit_key", None) == key:
            logger.debug("Skipping duplicate on-commit registration for %s", key)
            return False

    def run_once():
        callback()

    run_once._orders_on_commit_key = key
    transaction.on_commit(run_once)
    return True


def _enqueue_async_email_notification(order_pk, email_type, status_override=None, correlation_id=None):
    if not getattr(settings, "ORDER_ASYNC_NOTIFICATIONS_ENABLED", False):
        return False

    try:
        from .tasks import send_email_notification
    except ImportError:
        logger.warning("Celery task module unavailable, skipping async email dispatch for order %s", order_pk)
        return False

    try:
        send_email_notification.delay(
            order_pk,
            email_type,
            status=status_override,
            correlation_id=correlation_id,
        )
        return True
    except Exception as exc:
        logger.exception(
            "Failed to queue async email notification | order_id=%s | type=%s | error=%s",
            order_pk,
            email_type,
            exc,
        )
        return False


def _send_order_event_email_now(order_pk, event_type):
    from .services.email_service import send_order_email

    order = (
        Order.objects.select_related('user')
        .prefetch_related('items__product')
        .filter(pk=order_pk)
        .first()
    )
    if order is None:
        logger.warning("Skipping order event email because the order no longer exists | order_id=%s | event_type=%s", order_pk, event_type)
        return False

    return send_order_email(order, event_type)


def _schedule_order_event_email(order, event_type):
    try:
        scheduled = _schedule_on_commit_once(
            "order_event_email",
            (order.pk, event_type),
            lambda order_pk=order.pk, event_type=event_type: _send_order_event_email_now(order_pk, event_type),
        )
        if not scheduled:
            logger.info("Duplicate order event email skipped before commit | order_id=%s | event_type=%s", order.pk, event_type)
    except Exception as exc:
        logger.exception(
            "Failed to schedule order event email | order_id=%s | event_type=%s | error=%s",
            order.pk,
            event_type,
            exc,
        )


def queue_whatsapp_notification(order, status):
    try:
        correlation_id = get_correlation_id()
        _schedule_on_commit_once(
            "whatsapp",
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
    """Queue email after commit so notifications only fire for persisted orders."""
    try:
        correlation_id = get_correlation_id()

        from .services.email_service import _get_notification_fields

        if email_type in ("confirmation", "payment", "admin"):
            sent_field, _, _ = _get_notification_fields(email_type)
            if Order.objects.filter(pk=order.pk).values_list(sent_field, flat=True).first():
                logger.info("Email already sent | type=%s | order=%s | skipping", email_type, order.pk)
                return

        scheduled = _schedule_on_commit_once(
            "email",
            (order.pk, email_type, status_override or ""),
            lambda order_pk=order.pk, email_type=email_type, status_override=status_override, correlation_id=correlation_id: _send_email_notification_with_fallback(
                order_pk,
                email_type,
                status_override,
                correlation_id=correlation_id,
            ),
        )
        if not scheduled:
            logger.info(
                "Duplicate email on-commit notification skipped | order_id=%s | type=%s | status=%s",
                order.pk,
                email_type,
                status_override or "-",
            )
    except Exception as exc:
        logger.error("Failed to queue email notification for order %s: %s", order.id, exc)


def _send_email_notification_with_fallback(order_pk, email_type, status_override=None, correlation_id=None):
    try:
        sent_async = _enqueue_async_email_notification(
            order_pk,
            email_type,
            status_override,
            correlation_id=correlation_id,
        )
        logger.info("Email async queued: %s for order %s", sent_async, order_pk)

        if not sent_async:
            try:
                _send_email_instant(
                    order_pk,
                    email_type,
                    status_override,
                    correlation_id=correlation_id,
                )
            except Exception:
                logger.exception("Fallback email send failed for order %s", order_pk)
    except Exception:
        logger.exception("Email notification failed completely for order %s, attempting sync fallback", order_pk)
        try:
            _send_email_instant(
                order_pk,
                email_type,
                status_override,
                correlation_id=correlation_id,
            )
        except Exception:
            logger.exception("Emergency fallback email send failed for order %s", order_pk)


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
            logger.info("Retrying sync email send | type=%s | order=%s", email_type, order_pk)
            try:
                sent = send_notification_email(
                    order_pk,
                    email_type,
                    status=status_override,
                    raise_on_failure=True,
                )
                logger.info("Email retry success | type=%s | order=%s | sent=%s", email_type, order_pk, sent)
            except Exception as retry_exc:
                logger.error("Email retry failed | type=%s | order=%s | error=%s", email_type, order_pk, retry_exc)
                raise
        except Exception as exc:
            logger.exception("Failed to send instant email for order %s: %s", order_pk, exc)
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

        if _is_paid_fulfillment_stage(instance.status, instance.payment_status):
            logger.info(
                "Paid order detected on create | order=%s | status=%s | payment=%s",
                instance.id,
                instance.status,
                instance.payment_status,
            )
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
            queue_email_notification(instance, "confirmation")
            queue_email_notification(instance, "payment")
            queue_email_notification(instance, "admin")
            queue_whatsapp_notification(instance, "created")
            logger.info("Notifications triggered for new paid order #%s", instance.id)
        return

    if not hasattr(instance, "_previous_status"):
        instance._previous_status = None
        instance._previous_payment_status = None

    old_status = instance._previous_status
    new_status = instance.status
    prev_pay = getattr(instance, "_previous_payment_status", None)

    if old_status is None:
        if hasattr(instance, "_admin_old_status"):
            old_status = instance._admin_old_status
            prev_pay = getattr(instance, "_admin_old_payment_status", None)
        else:
            try:
                old_order = Order.objects.get(pk=instance.pk)
                old_status = old_order.status
                prev_pay = old_order.payment_status
            except Order.DoesNotExist:
                old_status = None
                prev_pay = None

    logger.info(
        "Status check | Order #%s | old_status=%s, new_status=%s | old_pay=%s, new_pay=%s",
        instance.id,
        old_status,
        new_status,
        prev_pay,
        instance.payment_status,
    )

    if old_status == new_status and prev_pay == instance.payment_status:
        logger.info("No status change for order #%s, skipping notifications", instance.id)
        return

    logger.info(
        "Status change detected | Order #%s | %s -> %s | pay:%s -> %s",
        instance.id,
        old_status,
        new_status,
        prev_pay,
        instance.payment_status,
    )

    entered_paid_fulfillment = not _is_paid_fulfillment_stage(old_status, prev_pay) and _is_paid_fulfillment_stage(
        instance.status,
        instance.payment_status,
    )

    if entered_paid_fulfillment:
        logger.info("Paid confirmation trigger | order=%s", instance.id)
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
        queue_email_notification(instance, "confirmation")
        queue_email_notification(instance, "payment")
        queue_email_notification(instance, "admin")
        queue_whatsapp_notification(instance, "created")
        logger.info("Notifications triggered for paid order #%s", instance.id)
        return

    from .services.email_service import get_order_status_email_event

    status_event = get_order_status_email_event(new_status)
    if status_event == "confirmed":
        _schedule_order_event_email(instance, status_event)
        queue_whatsapp_notification(instance, "packed")
        logger.info("Packed notifications queued for order #%s", instance.id)
    elif status_event == "shipped":
        _schedule_order_event_email(instance, status_event)
        queue_whatsapp_notification(instance, "shipped")
        logger.info("Shipped notifications queued for order #%s", instance.id)
    elif status_event == "delivered":
        _schedule_order_event_email(instance, status_event)
        queue_whatsapp_notification(instance, "delivered")
        logger.info("Delivered notifications queued for order #%s", instance.id)
    elif status_event == "cancelled":
        _schedule_order_event_email(instance, status_event)
        logger.info("Cancelled email queued for order #%s", instance.id)


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
