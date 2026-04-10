import re
import logging

from accounts.utils.email import send_email
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppSendError(Exception):
    """Raised when a WhatsApp send attempt fails after validation succeeded."""


def send_whatsapp_message(order, status):
    try:
        from .models import WhatsAppSettings
        settings_obj = WhatsAppSettings.get_settings()
    except Exception as e:
        logger.warning(f"WhatsApp settings table error | Order #{getattr(order, 'id', 'N/A')} | Error: {e}")
        return False
    
    if not settings_obj:
        logger.warning(f"WhatsApp settings not found | Order #{getattr(order, 'id', 'N/A')} | Create WhatsAppSettings in admin")
        return False
    
    if not settings_obj.is_active:
        logger.info(f"WhatsApp disabled | Order #{getattr(order, 'id', 'N/A')} | Enable in WhatsApp Settings admin")
        return False
    
    if not settings_obj.account_sid or not settings_obj.auth_token:
        logger.warning(f"WhatsApp credentials missing | Order #{getattr(order, 'id', 'N/A')} | Configure account_sid and auth_token")
        return False
    
    if not settings_obj.whatsapp_number:
        logger.warning(f"WhatsApp number not set | Order #{getattr(order, 'id', 'N/A')} | Configure whatsapp_number")
        return False
    
    if not order.phone_number:
        logger.warning(f"WhatsApp message skipped | Order #{order.id} | No phone number")
        return False
    
    # Normalize diverse phone formats into a canonical international form for Twilio.
    phone = order.phone_number.strip()
    phone_digits = re.sub(r'\D', '', phone)
    if not phone_digits:
        logger.warning(f"WhatsApp message skipped | Order #{order.id} | Invalid phone number format")
        return False

    if len(phone_digits) == 10:
        phone_digits = '91' + phone_digits
    phone = f'+{phone_digits}'

    template_map = {
        'paid': settings_obj.order_created_template,
        'packed': settings_obj.processing_template,
        'created': settings_obj.order_created_template,
        'processing': settings_obj.processing_template,
        'shipped': settings_obj.shipped_template,
        'delivered': settings_obj.delivered_template,
    }
    
    template = template_map.get(status)
    if not template:
        logger.warning(f"WhatsApp message skipped | Order #{order.id} | Unknown status: {status}")
        return False
    
    customer_name = order.customer_name or (order.user.username if order.user else 'Customer')
    
    try:
        message_body = template.format(
            name=customer_name,
            order_id=order.id,
            total=order.total_price
        )
    except KeyError as e:
        logger.error(f"WhatsApp template error | Order #{order.id} | Missing placeholder: {e}")
        message_body = template
    
    try:
        from twilio.rest import Client
        client = Client(settings_obj.account_sid, settings_obj.auth_token)
        
        client.messages.create(
            body=message_body,
            from_=f'whatsapp:{settings_obj.whatsapp_number}',
            to=f'whatsapp:{phone}'
        )
        
        logger.info(f"WhatsApp message sent | Order #{order.id} | Status: {status} | Phone: {phone}")
        return True
        
    except ImportError:
        logger.error(f"Twilio not installed | Order #{order.id} | Run: pip install twilio")
        return False
    except Exception as e:
        logger.exception(f"WhatsApp message FAILED | Order #{order.id} | Status: {status} | Error: {e}")
        raise WhatsAppSendError(e)


def _render_order_items_text(order):
    items_text = ''
    for item in order.items.select_related('product').all():
        items_text += f"- {item.product.name} (Qty: {item.quantity})"
        if getattr(item, 'size', None):
            items_text += f" - Size: {item.size}"
        items_text += f" - Rs.{item.subtotal:.2f}\n"
    return items_text


def _send_order_email(order, subject, message, recipient_list, *, email_type='generic'):
    if not recipient_list:
        logger.warning('Order email skipped: no recipients provided.')
        return False

    try:
        sent = send_email(
            subject=subject,
            message=message,
            recipient_list=recipient_list,
            from_email=settings.DEFAULT_FROM_EMAIL,
            email_type=email_type,
            user=getattr(order, 'user', None),
            order=order,
            metadata={'flow': 'legacy_order_email'},
        )
        if not sent:
            logger.error('Order email FAILED | Subject: %s | Recipients: %s', subject, recipient_list)
            return False
        logger.info('Order email sent | Subject: %s | Recipients: %s', subject, recipient_list)
        return True
    except Exception as e:
        logger.error('Order email FAILED | Subject: %s | Recipients: %s | Error: %s', subject, recipient_list, e)
        return False


def send_order_email(order, email_type='confirmation', status=None):
    if email_type == 'admin':
        recipient_list = [order.user.email] if getattr(order, 'user', None) and order.user.email else []
        subject = f'Order Created - #{order.id} - SYAFRA'
        message = f"""Hello {order.user.username if getattr(order, 'user', None) else 'Store Team'},

An order has been created for you by SYAFRA.

ORDER DETAILS
=============
Order ID: #{order.id}
Date: {order.created_at.strftime('%B %d, %Y')}

ITEMS:
{_render_order_items_text(order)}
Total: Rs.{order.total_price:.2f}

We will notify you once the order is processed.

Best regards,
SYAFRA Team
"""
        return _send_order_email(order, subject, message, recipient_list, email_type='admin_order_alert')

    recipient_list = [order.email] if getattr(order, 'email', None) else []
    if not recipient_list:
        logger.warning(f'Order email skipped | Order #{order.id} | No customer email')
        return False

    customer_name = order.customer_name or (order.user.username if getattr(order, 'user', None) else 'Customer')
    items_text = _render_order_items_text(order)
    order_date = order.created_at.strftime('%B %d, %Y')

    if email_type == 'confirmation':
        subject = f'Order Confirmation - #{order.id} - SYAFRA'
        message = f"""Hello {customer_name},

Thank you for your order! Your order has been received and is being processed.

ORDER DETAILS
============
Order ID: #{order.id}
Date: {order_date}

ITEMS:
{items_text}
Total: Rs.{order.total_price:.2f}

SHIPPING ADDRESS
================
{order.shipping_address}

Phone: {order.phone_number}

We will notify you once your order ships.

Thank you for shopping with SYAFRA!

Best regards,
SYAFRA Team
"""
        return _send_order_email(order, subject, message, recipient_list, email_type='order_confirmation')

    if email_type == 'payment':
        subject = f'Payment Confirmed - Order #{order.id} - SYAFRA'
        message = f"""Hello {customer_name},

Your payment for order #{order.id} has been successfully received.

ORDER DETAILS
============
Order ID: #{order.id}
Date: {order_date}

ITEMS:
{items_text}
Total: Rs.{order.total_price:.2f}

Payment ID: {order.razorpay_payment_id}

Thank you for shopping with SYAFRA!

Best regards,
SYAFRA Team
"""
        return _send_order_email(order, subject, message, recipient_list, email_type='payment_confirmation')

    if email_type == 'processing':
        subject = f'Your Order #{order.id} is Being Processed - SYAFRA'
        message = f"""Hello {customer_name},

Great news! Your order #{order.id} is now being processed.

ORDER DETAILS
============
Order ID: #{order.id}
Date: {order_date}

ITEMS:
{items_text}
Total: Rs.{order.total_price:.2f}

Our team is preparing your items for shipment. We'll notify you once the order ships.

Best regards,
SYAFRA Team
"""
        return _send_order_email(order, subject, message, recipient_list, email_type='order_status')

    status_value = status or order.status
    if email_type == 'status':
        if status_value in {'paid', 'confirmed'}:
            subject = f'Order #{order.id} Confirmed - SYAFRA'
            message = f"""Hello {customer_name},

Your order #{order.id} has been confirmed and is being prepared.

ORDER DETAILS
============
Order ID: #{order.id}
Date: {order_date}

ITEMS:
{items_text}
Total: Rs.{order.total_price:.2f}

Thank you for shopping with SYAFRA!

Best regards,
SYAFRA Team
"""
        elif status_value in {'packed', 'processing'}:
            subject = f'Your Order #{order.id} is Packed - SYAFRA'
            message = f"""Hello {customer_name},

Your order #{order.id} has been packed and is getting ready for shipment.

ORDER DETAILS
============
Order ID: #{order.id}
Date: {order_date}

ITEMS:
{items_text}
Total: Rs.{order.total_price:.2f}

We will notify you once your package has been shipped.

Best regards,
SYAFRA Team
"""
        elif status_value == 'shipped':
            subject = f'Your Order #{order.id} Has Been Shipped - SYAFRA'
            message = f"""Hello {customer_name},

Good news! Your order #{order.id} has been shipped.

ORDER DETAILS
============
Order ID: #{order.id}
Date: {order_date}

ITEMS:
{items_text}
Total: Rs.{order.total_price:.2f}

Shipping Address:
{order.shipping_address}

We'll share tracking details shortly.

Best regards,
SYAFRA Team
"""
        elif status_value == 'delivered':
            subject = f'Your Order #{order.id} Has Been Delivered - SYAFRA'
            message = f"""Hello {customer_name},

Your order #{order.id} has been delivered successfully.

ORDER DETAILS
============
Order ID: #{order.id}
Date: {order_date}

ITEMS:
{items_text}
Total: Rs.{order.total_price:.2f}

We hope you enjoy your purchase.

Best regards,
SYAFRA Team
"""
        elif status_value == 'cancelled':
            subject = f'Order #{order.id} Cancelled - SYAFRA'
            message = f"""Hello {customer_name},

Your order #{order.id} has been cancelled.

If you have questions, please contact support.

Best regards,
SYAFRA Team
"""
        else:
            subject = f'Order Update - Order #{order.id} - SYAFRA'
            message = f"""Hello {customer_name},

Your order #{order.id} status has been updated to {order.get_status_display()}.

Thank you for shopping with SYAFRA.

Best regards,
SYAFRA Team
"""
        return _send_order_email(order, subject, message, recipient_list, email_type='order_status')

    logger.warning(f'Unknown email_type requested: {email_type}')
    return False


def send_order_confirmation_email(order):
    return send_order_email(order, 'confirmation')


def send_admin_order_email(order):
    return send_order_email(order, 'admin')


def send_processing_email(order):
    return send_order_email(order, 'processing')


def send_status_update_email(order, status):
    return send_order_email(order, 'status', status=status)
