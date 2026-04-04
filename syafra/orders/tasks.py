import logging

try:
    from celery import shared_task
    from celery.utils.log import get_task_logger
except ImportError:
    def get_task_logger(name):
        return logging.getLogger(name)

    class _FallbackTask:
        def __init__(self, func, bind=False):
            self._func = func
            self._bind = bind
            self.__name__ = getattr(func, '__name__', 'task')
            self.__doc__ = getattr(func, '__doc__')

        def __call__(self, *args, **kwargs):
            return self.run(*args, **kwargs)

        def delay(self, *args, **kwargs):
            raise RuntimeError('Celery is not installed; async task dispatch is unavailable.')

        def retry(self, exc=None, countdown=None):
            if exc is not None:
                raise exc
            raise RuntimeError('Celery retry requested but Celery is not installed.')

        def run(self, *args, **kwargs):
            if self._bind:
                return self._func(self, *args, **kwargs)
            return self._func(*args, **kwargs)

    def shared_task(*decorator_args, **decorator_kwargs):
        bind = decorator_kwargs.get('bind', False)

        if decorator_args and callable(decorator_args[0]) and len(decorator_args) == 1 and not decorator_kwargs:
            return _FallbackTask(decorator_args[0], bind=False)

        def decorator(func):
            return _FallbackTask(func, bind=bind)

        return decorator

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from syafra.logging_context import correlation_id_context

from .models import Order
from .utils import WhatsAppSendError, send_whatsapp_message

logger = get_task_logger(__name__)


def send_email_sync(order_id, email_type, status=None, max_attempts=None, correlation_id=None):
    """
    Send email synchronously via the shared email service helper.

    The sync fallback is still best-effort, but it retries a couple of times so
    a transient backend failure does not immediately drop the notification.
    """
    from .services.email_service import EmailDeliveryError, send_notification_email

    max_attempts = max_attempts or max(getattr(settings, 'ORDER_NOTIFICATION_SYNC_RETRY_ATTEMPTS', 2), 1)
    last_error = None
    with correlation_id_context(correlation_id):
        for attempt in range(1, max_attempts + 1):
            try:
                sent = send_notification_email(
                    order_id,
                    email_type,
                    status=status,
                    raise_on_failure=True,
                )
                logger.info(
                    "Sync email delivery completed | order_id=%s | type=%s | attempt=%s | sent=%s",
                    order_id,
                    email_type,
                    attempt,
                    sent,
                )
                return sent
            except EmailDeliveryError as exc:
                last_error = exc
                logger.warning(
                    "Sync email delivery failed | order_id=%s | type=%s | attempt=%s | error=%s",
                    order_id,
                    email_type,
                    attempt,
                    exc,
                )

    if last_error:
        raise last_error
    return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification(self, order_id, email_type, status=None, correlation_id=None):
    """
    Async email delivery with retry support.
    """
    from .services.email_service import EmailDeliveryError, send_notification_email

    with correlation_id_context(correlation_id):
        try:
            sent = send_notification_email(order_id, email_type, status=status, raise_on_failure=True)
            logger.info("Email task completed | order_id=%s | type=%s | sent=%s", order_id, email_type, sent)
            return sent
        except EmailDeliveryError as exc:
            retry_count = getattr(getattr(self, 'request', None), 'retries', 0)
            countdown = min(60 * (retry_count + 1), 300)
            logger.warning(
                "Retrying email task | order_id=%s | type=%s | retry_count=%s | error=%s",
                order_id,
                email_type,
                retry_count,
                exc,
            )
            raise self.retry(exc=exc, countdown=countdown)
        except Exception as exc:
            logger.exception(
                "Unexpected error in email task | order_id=%s | type=%s | error=%s",
                order_id,
                email_type,
                exc,
            )
            raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_email(self, order_id, correlation_id=None):
    """
    Backwards-compatible wrapper for confirmation emails.
    """
    return send_email_notification.run(order_id, 'confirmation', correlation_id=correlation_id)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_payment_confirmation_email(self, order_id, correlation_id=None):
    """
    Backwards-compatible wrapper for payment emails.
    """
    return send_email_notification.run(order_id, 'payment', correlation_id=correlation_id)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_status_update_email(self, order_id, status, correlation_id=None):
    """
    Backwards-compatible wrapper for status emails.
    """
    return send_email_notification.run(order_id, 'status', status, correlation_id=correlation_id)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_whatsapp_notification(self, order_id, status, correlation_id=None):
    with correlation_id_context(correlation_id):
        try:
            order = Order.objects.get(pk=order_id)
        except ObjectDoesNotExist:
            logger.warning("WhatsApp task skipped: order %s not found", order_id)
            return False

        try:
            sent = send_whatsapp_message(order, status)
            if not sent:
                logger.warning(
                    "WhatsApp send returned False without a retryable error | Order %s | Status %s",
                    order_id,
                    status,
                )
                return False
            return True
        except WhatsAppSendError as exc:
            logger.warning(
                "WhatsApp send failed, retrying | Order %s | Status %s | Error: %s",
                order_id,
                status,
                exc,
            )
            raise self.retry(exc=exc)
        except Exception as exc:
            logger.exception(
                "Unexpected error in WhatsApp task | Order %s | Status %s | Error: %s",
                order_id,
                status,
                exc,
            )
            raise self.retry(exc=exc)
