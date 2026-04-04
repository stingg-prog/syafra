import logging
import re
from datetime import timedelta
from uuid import uuid4

import razorpay
from razorpay import errors as razorpay_errors
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from cart.models import Cart

from .forms import CheckoutForm
from .models import Order, OrderItem, PaymentSettings
from .services.order_service import confirm_order_payment, lock_inventory_rows

logger = logging.getLogger(__name__)

UPI_TRANSACTION_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/-]{7,63}$')
PAYMENT_RETRY_RESERVATION_PREFIX = 'retry_res_'


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _format_log_message(message, request=None, **context):
    parts = []
    if request is not None:
        user_id = request.user.id if getattr(request.user, 'is_authenticated', False) else 'anonymous'
        parts.extend([
            f'user_id={user_id}',
            f'method={request.method}',
            f'path={request.path}',
        ])
        client_ip = _get_client_ip(request)
        if client_ip:
            parts.append(f'client_ip={client_ip}')

    for key, value in context.items():
        if value not in (None, ''):
            parts.append(f'{key}={value}')

    if not parts:
        return message
    return f"{message} | {' | '.join(parts)}"


def _redact_reference(value, keep=6):
    if not value:
        return ''
    value = str(value)
    if len(value) <= keep:
        return value
    return f"...{value[-keep:]}"


def _normalize_upi_transaction_id(value):
    return (value or '').strip()


def _is_valid_upi_transaction_id(value):
    return bool(UPI_TRANSACTION_ID_RE.fullmatch(value))


def _make_payment_retry_reservation(order_id):
    return f"{PAYMENT_RETRY_RESERVATION_PREFIX}{order_id}_{uuid4().hex[:24]}"


def _is_payment_retry_reservation(value):
    return bool(value) and value.startswith(PAYMENT_RETRY_RESERVATION_PREFIX)


def _get_payment_retry_timeout():
    return timedelta(seconds=max(getattr(settings, 'ORDER_PAYMENT_RETRY_TIMEOUT_SECONDS', 900), 1))


def _is_payment_retry_expired(order, now=None):
    now = now or timezone.now()
    if not order.payment_retry_reserved_at:
        return False
    return order.payment_retry_reserved_at < now - _get_payment_retry_timeout()


def _checkout_context(*, cart, items, total, currency, payment_settings, payment_notice, cod_fallback, form, available_methods, upi_enabled):
    return {
        'cart': cart,
        'items': items,
        'total': total,
        'currency': currency,
        'payment_settings': payment_settings,
        'payment_notice': payment_notice,
        'cod_fallback': cod_fallback,
        'form': form,
        'available_methods': available_methods,
        'upi_enabled': upi_enabled,
    }


@login_required
def checkout(request):
    cart = Cart.get_for_user(request.user)
    items = list(cart.items.select_related('product').all())
    cart_total = sum(item.quantity * item.product.price for item in items)
    if not items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart:cart_view')

    payment_settings = PaymentSettings.get_settings()
    if payment_settings:
        razorpay_key_id = payment_settings.resolved_razorpay_key_id
        razorpay_key_secret = payment_settings.resolved_razorpay_key_secret
    else:
        razorpay_key_id, razorpay_key_secret = PaymentSettings.get_env_razorpay_credentials()

    currency = payment_settings.currency_symbol if payment_settings else '\u20b9'
    currency_code = payment_settings.currency if payment_settings else 'INR'
    can_pay_online = bool(
        (payment_settings.is_active if payment_settings else True)
        and razorpay_key_id
        and razorpay_key_secret
    )
    upi_enabled = bool(payment_settings and payment_settings.upi_enabled and payment_settings.upi_id)
    upi_id = payment_settings.upi_id if upi_enabled else ''

    available_methods = []
    if can_pay_online:
        available_methods.append('razorpay')
    if upi_enabled:
        available_methods.append('upi')

    cod_fallback = False
    payment_notice = ''
    if payment_settings and payment_settings.payment_disabled_message and not can_pay_online and not upi_enabled:
        payment_notice = payment_settings.payment_disabled_message

    def render_checkout(form):
        return render(
            request,
            'checkout.html',
            _checkout_context(
                cart=cart,
                items=items,
                total=cart_total,
                currency=currency,
                payment_settings=payment_settings,
                payment_notice=payment_notice,
                cod_fallback=cod_fallback,
                form=form,
                available_methods=available_methods,
                upi_enabled=upi_enabled,
            ),
        )

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
            return render_checkout(form)

        customer_name = form.cleaned_data['customer_name']
        email = form.cleaned_data['email']
        phone_number = form.cleaned_data['phone_number']
        shipping_address = form.cleaned_data['shipping_address']
        pincode = form.cleaned_data['pincode']
        payment_method = form.cleaned_data.get('payment_method', 'razorpay') or 'razorpay'

        logger.info(
            _format_log_message(
                "Checkout submission received",
                request,
                payment_method=payment_method,
                can_pay_online=can_pay_online,
                upi_enabled=upi_enabled,
                available_methods=','.join(available_methods),
            )
        )

        if payment_method == 'razorpay' and not can_pay_online:
            logger.error(_format_log_message("Razorpay not available for checkout", request))
            messages.error(request, 'Razorpay payment is not available. Please contact support.')
            return render_checkout(form)

        if payment_method == 'upi' and not upi_enabled:
            logger.warning(_format_log_message("UPI not available for checkout", request))
            messages.error(request, 'UPI payment is not available. Please contact support.')
            return render_checkout(form)

        try:
            with transaction.atomic():
                locked_cart = Cart.objects.select_for_update().get(pk=cart.pk, user=request.user)
                locked_items = list(
                    locked_cart.items.select_related('product').select_for_update().order_by('product_id', 'size', 'id')
                )
                if not locked_items:
                    raise ValueError('Your cart is empty.')

                locked_cart_total = sum(item.quantity * item.product.price for item in locked_items)
                if locked_cart_total <= 0:
                    raise ValueError('Invalid order total. Please refresh your cart.')

                order = Order.objects.create(
                    user=request.user,
                    total_price=locked_cart_total,
                    customer_name=customer_name,
                    email=email,
                    phone_number=phone_number,
                    shipping_address=f"{shipping_address}\nPincode: {pincode}",
                    status='pending',
                    payment_status='pending',
                )
                logger.info(
                    _format_log_message(
                        "Order created from checkout",
                        request,
                        order_id=order.id,
                        total=locked_cart_total,
                    )
                )

                ordered_items, locked_products, locked_sizes = lock_inventory_rows(locked_items)
                order_items = []
                locked_item_ids = []
                for cart_item in ordered_items:
                    locked_item_ids.append(cart_item.pk)
                    product = locked_products.get(cart_item.product_id)
                    if not product:
                        raise ValueError(
                            f"Product for cart item {cart_item.product_id} is no longer available. Please refresh your cart."
                        )

                    if product.stock < cart_item.quantity:
                        raise ValueError(
                            f"Insufficient stock for {product.name}. Available: {product.stock}, Requested: {cart_item.quantity}"
                        )

                    if cart_item.size:
                        product_size = locked_sizes.get((cart_item.product_id, cart_item.size))
                        if not product_size:
                            raise ValueError(
                                f"Selected size {cart_item.size} for {product.name} is no longer available."
                            )
                        if product_size.stock < cart_item.quantity:
                            raise ValueError(
                                f"Insufficient stock for size {cart_item.size}. Available: {product_size.stock}, Requested: {cart_item.quantity}"
                            )

                    order_items.append(
                        OrderItem(
                            order=order,
                            product=product,
                            quantity=cart_item.quantity,
                            price=product.price,
                            size=cart_item.size,
                        )
                    )

                OrderItem.objects.bulk_create(order_items)
                locked_cart.items.filter(pk__in=locked_item_ids).delete()

        except (ValueError, TypeError, KeyError) as exc:
            logger.error(
                _format_log_message(
                    "Checkout validation error",
                    request,
                    error_type=type(exc).__name__,
                    error=exc,
                )
            )
            messages.error(
                request,
                str(exc) if isinstance(exc, ValueError) else 'Invalid order data. Please refresh and try again.',
            )
            return render_checkout(form)
        except (DatabaseError, IntegrityError) as exc:
            logger.exception(_format_log_message("Checkout database failure", request, error=exc))
            messages.error(request, f'Database error: {str(exc)[:100]}. Please try again.')
            return render_checkout(form)
        except Exception as exc:
            logger.exception(_format_log_message("Unexpected checkout error", request, error=exc))
            messages.error(request, 'An unexpected error occurred during checkout. Please try again.')
            return render_checkout(form)

        if payment_method == 'razorpay' and can_pay_online:
            logger.info(_format_log_message("Processing Razorpay payment", request, order_id=order.id))
            try:
                client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
                razorpay_order = client.order.create({
                    'amount': int(float(order.total_price) * 100),
                    'currency': currency_code,
                    'receipt': f'order_{order.id}',
                    'payment_capture': '1',
                })
            except (razorpay_errors.BadRequestError, razorpay_errors.ServerError, razorpay_errors.GatewayError) as exc:
                logger.error(
                    _format_log_message("Razorpay API error during checkout", request, order_id=order.id, error=exc)
                )
                messages.error(request, 'Payment service error. Please try again in a moment.')
                return redirect(reverse('orders:payment_failed') + f'?order_id={order.id}')
            except Exception as exc:
                logger.exception(
                    _format_log_message("Unexpected Razorpay error during checkout", request, order_id=order.id, error=exc)
                )
                messages.error(request, 'An unexpected payment error occurred. Please try again.')
                return redirect(reverse('orders:payment_failed') + f'?order_id={order.id}')

            Order.objects.filter(pk=order.pk).update(razorpay_order_id=razorpay_order['id'])
            order.razorpay_order_id = razorpay_order['id']
            logger.info(
                _format_log_message(
                    "Rendering Razorpay payment page",
                    request,
                    order_id=order.id,
                    razorpay_order_id=order.razorpay_order_id,
                )
            )

            return render(request, 'payment.html', {
                'order': order,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key': razorpay_key_id,
                'amount': int(float(order.total_price) * 100),
                'currency_code': currency_code,
                'currency_symbol': currency,
            })

        if payment_method == 'upi' and upi_enabled:
            logger.info(_format_log_message("Rendering UPI payment page", request, order_id=order.id))
            try:
                upi_qr_code = None
                if payment_settings and payment_settings.upi_qr_code:
                    try:
                        upi_qr_code = payment_settings.upi_qr_code.url
                    except Exception as qr_err:
                        logger.warning(
                            _format_log_message("Could not resolve UPI QR code", request, order_id=order.id, error=qr_err)
                        )

                return render(request, 'upi_payment.html', {
                    'order': order,
                    'upi_id': upi_id,
                    'amount': order.total_price,
                    'currency_symbol': currency,
                    'upi_qr_code': upi_qr_code,
                })
            except Exception as exc:
                logger.exception(_format_log_message("Error rendering UPI payment page", request, order_id=order.id, error=exc))
                messages.error(request, f'UPI Error: {exc}')
                return redirect('cart:cart_view')

        messages.error(request, 'No payment method available. Please contact support.')
        return redirect('cart:cart_view')

    return render_checkout(CheckoutForm())


@login_required
def payment_success(request):
    """
    Handle Razorpay payment callback.
    Requires authentication and validates order ownership before processing.
    """
    if request.method != 'POST':
        logger.warning(_format_log_message("Payment success accessed via GET, redirecting", request))
        return redirect('cart:cart_view')
    
    razorpay_order_id = request.POST.get('razorpay_order_id', '')
    razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
    razorpay_signature = request.POST.get('razorpay_signature', '')

    logger.info(
        _format_log_message(
            "Payment callback received",
            request,
            razorpay_order_id=razorpay_order_id,
            payment_reference=_redact_reference(razorpay_payment_id),
        )
    )

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        logger.error(_format_log_message("Payment callback missing required fields", request))
        messages.error(request, 'Invalid payment callback.')
        return redirect('cart:cart_view')

    try:
        order = Order.objects.select_related('user').get(razorpay_order_id=razorpay_order_id)
    except Order.DoesNotExist:
        logger.error(
            _format_log_message("Order not found for payment callback", request, razorpay_order_id=razorpay_order_id)
        )
        messages.error(request, 'Order not found.')
        return redirect('cart:cart_view')

    if order.user_id != request.user.id:
        logger.warning(
            _format_log_message("Unauthorized payment attempt", request, order_id=order.id, owner_user_id=order.user_id)
        )
        messages.error(request, 'Unauthorized access to this order.')
        return redirect('cart:cart_view')

    if order.payment_status == 'paid':
        logger.info(_format_log_message("Duplicate paid callback ignored", request, order_id=order.id))
        return redirect('orders:order_success', order_id=order.id)

    payment_settings = PaymentSettings.get_settings()
    if not payment_settings:
        logger.error(_format_log_message("Payment settings not configured", request, order_id=order.id))
        messages.error(request, 'Payment system configuration error.')
        return redirect('cart:cart_view')

    razorpay_key_id = payment_settings.resolved_razorpay_key_id
    razorpay_key_secret = payment_settings.resolved_razorpay_key_secret
    if not razorpay_key_id or not razorpay_key_secret:
        logger.error(_format_log_message("Razorpay credentials missing", request, order_id=order.id))
        messages.error(request, 'Payment system configuration error.')
        return redirect('cart:cart_view')

    client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature,
    }

    try:
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError as exc:
        logger.error(
            _format_log_message(
                "Payment signature verification failed",
                request,
                order_id=order.id,
                payment_reference=_redact_reference(razorpay_payment_id),
                error=exc,
            )
        )
        Order.objects.filter(pk=order.pk).update(payment_status='failed')
        messages.error(request, 'Payment verification failed. Please try again.')
        return redirect('cart:cart_view')

    try:
        order, _processed = confirm_order_payment(order, payment_reference=razorpay_payment_id)
        logger.info(
            _format_log_message(
                "Payment verified successfully",
                request,
                order_id=order.id,
                payment_reference=_redact_reference(razorpay_payment_id),
            )
        )
    except Exception as exc:
        logger.exception(_format_log_message("Error processing order confirmation", request, order_id=order.id, error=exc))
        messages.error(request, 'Payment successful but order processing failed. Please contact support.')
        return redirect('cart:cart_view')

    messages.success(request, 'Payment successful! Your order has been confirmed.')
    return redirect('orders:order_success', order_id=order.id)


@login_required
def order_success(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__product'),
        id=order_id,
        user=request.user,
    )
    items = order.items.select_related('product').all()

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '\u20b9'

    return render(request, 'order_success.html', {
        'order': order,
        'items': items,
        'currency': currency,
    })


@login_required
def order_history(request):
    orders = (
        Order.objects.filter(user=request.user)
        .select_related('user')
        .prefetch_related('items__product')
        .order_by('-created_at')
    )
    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '\u20b9'
    return render(request, 'order_history.html', {
        'orders': orders,
        'currency': currency,
    })


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__product'),
        id=order_id,
        user=request.user,
    )
    items = order.items.select_related('product').all()

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '\u20b9'

    return render(request, 'order_detail.html', {
        'order': order,
        'items': items,
        'currency': currency,
    })


@login_required
@require_http_methods(['GET', 'HEAD', 'OPTIONS'])
def payment_failed(request):
    order_id = request.GET.get('order_id')
    return render(request, 'payment_failed.html', {'order_id': order_id})


@login_required
@require_http_methods(['GET', 'HEAD', 'OPTIONS'])
def retry_payment(request, order_id):
    payment_settings = PaymentSettings.get_settings()
    if not payment_settings or not payment_settings.is_active:
        logger.warning(_format_log_message("Retry payment blocked because payment system is inactive", request, order_id=order_id))
        messages.error(request, 'Payment system is currently unavailable.')
        return redirect('cart:cart_view')

    razorpay_key_id = payment_settings.resolved_razorpay_key_id
    razorpay_key_secret = payment_settings.resolved_razorpay_key_secret
    if not razorpay_key_id or not razorpay_key_secret:
        logger.error(_format_log_message("Retry payment attempted without valid Razorpay credentials", request, order_id=order_id))
        messages.error(request, 'Payment gateway credentials are missing. Please contact support.')
        return redirect('cart:cart_view')

    existing_gateway_order_id = ''
    reservation_id = ''
    reservation_started_at = None

    try:
        with transaction.atomic(savepoint=False):
            order = Order.objects.select_for_update().get(id=order_id, user=request.user)
            now = timezone.now()

            if order.payment_status == 'paid':
                logger.info(_format_log_message("Retry payment ignored for paid order", request, order_id=order.id))
                return redirect('orders:order_success', order_id=order.id)

            update_fields = []
            retry_expired = _is_payment_retry_expired(order, now=now)
            reservation_missing_timestamp = (
                _is_payment_retry_reservation(order.razorpay_order_id)
                and order.payment_retry_reserved_at is None
            )

            if retry_expired or reservation_missing_timestamp:
                logger.info(
                    _format_log_message(
                        "Expiring stale payment retry session",
                        request,
                        order_id=order.id,
                        razorpay_order_id=order.razorpay_order_id,
                    )
                )
                if order.razorpay_order_id:
                    order.razorpay_order_id = ''
                    update_fields.append('razorpay_order_id')
                order.payment_retry_reserved_at = None
                update_fields.append('payment_retry_reserved_at')

            if order.razorpay_order_id and _is_payment_retry_reservation(order.razorpay_order_id):
                logger.warning(
                    _format_log_message(
                        "Duplicate payment retry blocked while reservation exists",
                        request,
                        order_id=order.id,
                    )
                )
                if update_fields:
                    order.save(update_fields=list(dict.fromkeys(update_fields)))
                messages.info(request, 'A payment retry is already being prepared. Please refresh in a moment.')
                return redirect(reverse('orders:payment_failed') + f'?order_id={order.id}')

            if order.razorpay_order_id and not _is_payment_retry_reservation(order.razorpay_order_id):
                existing_gateway_order_id = order.razorpay_order_id
                if order.payment_status != 'pending':
                    order.payment_status = 'pending'
                    update_fields.append('payment_status')
                if order.status != 'pending':
                    order.status = 'pending'
                    update_fields.append('status')
            else:
                reservation_id = _make_payment_retry_reservation(order.id)
                reservation_started_at = now
                order.razorpay_order_id = reservation_id
                order.payment_status = 'pending'
                order.status = 'pending'
                order.payment_retry_reserved_at = reservation_started_at
                update_fields.extend(['razorpay_order_id', 'payment_status', 'status', 'payment_retry_reserved_at'])

            if update_fields:
                order.save(update_fields=list(dict.fromkeys(update_fields)))
    except Order.DoesNotExist:
        logger.warning(_format_log_message("Retry payment requested for missing order", request, order_id=order_id))
        messages.error(request, 'Order not found.')
        return redirect('cart:cart_view')

    if existing_gateway_order_id:
        order.razorpay_order_id = existing_gateway_order_id
        logger.info(
            _format_log_message(
                "Reusing existing gateway order for retry payment",
                request,
                order_id=order.id,
                razorpay_order_id=existing_gateway_order_id,
            )
        )
        return render(request, 'retry_payment.html', {
            'order': order,
            'razorpay_order_id': existing_gateway_order_id,
            'razorpay_key': razorpay_key_id,
            'amount': int(float(order.total_price) * 100),
            'currency_code': payment_settings.currency,
            'currency_symbol': payment_settings.currency_symbol,
        })

    try:
        client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
        razorpay_order = client.order.create({
            'amount': int(float(order.total_price) * 100),
            'currency': payment_settings.currency,
            'receipt': f'order_{order.id}_retry',
            'payment_capture': '1',
        })
    except (razorpay_errors.BadRequestError, razorpay_errors.ServerError, razorpay_errors.GatewayError) as exc:
        Order.objects.filter(pk=order.pk, razorpay_order_id=reservation_id).update(
            razorpay_order_id='',
            payment_status='failed',
            payment_retry_reserved_at=None,
        )
        logger.error(_format_log_message("Razorpay API error during retry checkout", request, order_id=order.id, error=exc))
        messages.error(request, 'Payment service error. Please try again in a moment.')
        return redirect(reverse('orders:payment_failed') + f'?order_id={order.id}')
    except Exception as exc:
        Order.objects.filter(pk=order.pk, razorpay_order_id=reservation_id).update(
            razorpay_order_id='',
            payment_status='failed',
            payment_retry_reserved_at=None,
        )
        logger.exception(_format_log_message("Unexpected error while retrying payment", request, order_id=order.id, error=exc))
        messages.error(request, 'An unexpected error occurred. Please try again.')
        return redirect(reverse('orders:payment_failed') + f'?order_id={order.id}')

    updated = Order.objects.filter(
        pk=order.pk,
        razorpay_order_id=reservation_id,
        payment_retry_reserved_at=reservation_started_at,
    ).update(
        razorpay_order_id=razorpay_order['id'],
        payment_status='pending',
        status='pending',
        payment_retry_reserved_at=reservation_started_at,
    )
    if not updated:
        logger.warning(
            _format_log_message(
                "Retry reservation was replaced before gateway order could be saved",
                request,
                order_id=order.id,
            )
        )
        order.refresh_from_db(fields=['razorpay_order_id', 'payment_status', 'status', 'payment_retry_reserved_at'])
        if _is_payment_retry_reservation(order.razorpay_order_id) or not order.razorpay_order_id:
            messages.info(request, 'A payment retry is already being prepared. Please refresh in a moment.')
            return redirect(reverse('orders:payment_failed') + f'?order_id={order.id}')
    else:
        order.razorpay_order_id = razorpay_order['id']
        order.payment_retry_reserved_at = reservation_started_at

    logger.info(
        _format_log_message(
            "Retry payment initiated",
            request,
            order_id=order.id,
            razorpay_order_id=order.razorpay_order_id,
        )
    )

    return render(request, 'retry_payment.html', {
        'order': order,
        'razorpay_order_id': order.razorpay_order_id,
        'razorpay_key': razorpay_key_id,
        'amount': int(float(order.total_price) * 100),
        'currency_code': payment_settings.currency,
        'currency_symbol': payment_settings.currency_symbol,
    })


@login_required
def upi_payment_verify(request):
    if request.method != 'POST':
        logger.warning(_format_log_message("UPI verify accessed via GET, redirecting", request))
        return redirect('cart:cart_view')
    
    order_id = request.POST.get('order_id', '')
    transaction_id = _normalize_upi_transaction_id(request.POST.get('transaction_id', ''))

    if not order_id or not transaction_id:
        logger.warning(_format_log_message("UPI verification missing required fields", request, order_id=order_id))
        messages.error(request, 'Missing order or transaction details.')
        return redirect('cart:cart_view')

    if not _is_valid_upi_transaction_id(transaction_id):
        logger.warning(
            _format_log_message(
                "Rejected invalid UPI transaction id",
                request,
                order_id=order_id,
                payment_reference=_redact_reference(transaction_id),
            )
        )
        messages.error(request, 'Enter a valid UPI transaction ID.')
        return redirect('cart:cart_view')

    try:
        order = Order.objects.select_related('user').get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        logger.warning(_format_log_message("UPI verification requested for missing order", request, order_id=order_id))
        messages.error(request, 'Order not found.')
        return redirect('cart:cart_view')

    if order.payment_status == 'paid':
        logger.info(_format_log_message("Duplicate UPI verification ignored", request, order_id=order.id))
        messages.info(request, 'This order is already paid.')
        return redirect('orders:order_success', order_id=order.id)

    try:
        order, _processed = confirm_order_payment(order, payment_reference=f'UPI-{transaction_id}')
        logger.info(
            _format_log_message(
                "UPI payment verified successfully",
                request,
                order_id=order.id,
                payment_reference=_redact_reference(transaction_id),
            )
        )
    except Exception as exc:
        logger.exception(_format_log_message("Error processing UPI order confirmation", request, order_id=order.id, error=exc))
        messages.error(request, 'Payment verified but order processing failed. Please contact support.')
        return redirect('cart:cart_view')

    messages.success(request, 'Payment verified! Your order has been confirmed.')
    return redirect('orders:order_success', order_id=order.id)
