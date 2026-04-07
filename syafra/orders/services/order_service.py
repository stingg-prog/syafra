"""
Order service helpers for stock and payment finalization.
"""
import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from orders.models import Order, OrderItem, PAID_FULFILLMENT_STATUSES
from products.models import Product, ProductSize

logger = logging.getLogger(__name__)


def _hydrate_order_instance(target, source):
    """Keep the caller's model instance in sync with the locked DB row."""
    if target is source:
        return source
    for field in source._meta.concrete_fields:
        setattr(target, field.attname, getattr(source, field.attname))
    return source


def sort_inventory_items(items):
    """
    Sort inventory rows in a single deterministic order to prevent deadlocks.

    Every flow that locks product inventory should acquire those locks in the
    same sequence: product id, then size, then row id.
    """
    return sorted(
        list(items),
        key=lambda item: (
            item.product_id,
            item.size or '',
            item.pk or 0,
        ),
    )


def get_locked_order(order_or_id):
    order_id = getattr(order_or_id, 'pk', order_or_id)
    return Order.objects.select_for_update().select_related('user').get(pk=order_id)


def get_locked_order_items(order_or_id):
    order_id = getattr(order_or_id, 'pk', order_or_id)
    return list(
        OrderItem.objects.select_for_update()
        .select_related('product')
        .filter(order_id=order_id)
        .order_by('product_id', 'size', 'id')
    )


def _lock_order_for_stock_mutation(order):
    """
    Always acquire the order row before touching any inventory rows.
    """
    return get_locked_order(order)


def lock_inventory_rows(items):
    """
    Lock all product and size rows needed for a set of items using a strict,
    deterministic lock order and the minimum number of queries.
    """
    ordered_items = sort_inventory_items(items)
    if not ordered_items:
        return ordered_items, {}, {}

    product_ids = sorted({item.product_id for item in ordered_items})
    products = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=product_ids)
        .order_by('pk')
    }

    size_keys = sorted({(item.product_id, item.size) for item in ordered_items if item.size})
    product_sizes = {}
    if size_keys:
        size_filter = Q()
        for product_id, size in size_keys:
            size_filter |= Q(product_id=product_id, size=size)
        product_sizes = {
            (product_size.product_id, product_size.size): product_size
            for product_size in ProductSize.objects.select_for_update()
            .filter(size_filter)
            .order_by('product_id', 'size', 'pk')
        }

    return ordered_items, products, product_sizes


def _mutate_inventory(order, *, ordered_items, locked_products, locked_sizes, direction, force=False):
    quantity_multiplier = -1 if direction == 'reduce' else 1

    for item in ordered_items:
        product = locked_products.get(item.product_id)
        if not product:
            raise ValueError(f"Product {item.product_id} is no longer available.")

        quantity = item.quantity
        size = item.size

        if size:
            product_size = locked_sizes.get((item.product_id, size))
            if not product_size:
                if direction == 'reduce':
                    logger.warning(
                        "ProductSize not found during reduction | order_id=%s | user_id=%s | product_id=%s | size=%s",
                        order.id,
                        order.user_id,
                        item.product_id,
                        size,
                    )
                    raise ValueError(f"Size {size} not available for {product.name}")
                logger.warning(
                    "ProductSize not found during restore | order_id=%s | user_id=%s | product_id=%s | size=%s",
                    order.id,
                    order.user_id,
                    item.product_id,
                    size,
                )
            else:
                if direction == 'reduce' and not force and product_size.stock < quantity:
                    raise ValueError(
                        f"Insufficient stock for size {size} of {product.name}. "
                        f"Available: {product_size.stock}, Requested: {quantity}"
                    )
                product_size.stock += quantity_multiplier * quantity
                product_size.save(update_fields=['stock'])
                logger.info(
                    "%s size stock | order_id=%s | user_id=%s | product_id=%s | size=%s | quantity=%s",
                    "Reduced" if direction == 'reduce' else "Restored",
                    order.id,
                    order.user_id,
                    product.id,
                    size,
                    quantity,
                )

        if direction == 'reduce' and not force and product.stock < quantity:
            raise ValueError(
                f"Insufficient stock for {product.name}. "
                f"Available: {product.stock}, Requested: {quantity}"
            )

        product.stock += quantity_multiplier * quantity
        product.save(update_fields=['stock'])
        logger.info(
            "%s main stock | order_id=%s | user_id=%s | product_id=%s | quantity=%s",
            "Reduced" if direction == 'reduce' else "Restored",
            order.id,
            order.user_id,
            product.id,
            quantity,
        )


def reduce_stock(order, force=False, order_items=None):
    """
    Reduce main product stock and size-specific stock for each order item.
    """
    try:
        with transaction.atomic(savepoint=False):
            locked_order = _lock_order_for_stock_mutation(order)
            locked_items = order_items if order_items is not None else get_locked_order_items(locked_order)
            ordered_items, locked_products, locked_sizes = lock_inventory_rows(locked_items)
            _mutate_inventory(
                locked_order,
                ordered_items=ordered_items,
                locked_products=locked_products,
                locked_sizes=locked_sizes,
                direction='reduce',
                force=force,
            )
            return True

    except Exception as exc:
        logger.error(
            "Failed to reduce stock | order_id=%s | user_id=%s | error=%s",
            order.id,
            order.user_id,
            exc,
        )
        raise


def restore_stock(order, order_items=None):
    """
    Restore main product stock and size-specific stock for each order item.
    """
    try:
        with transaction.atomic(savepoint=False):
            locked_order = _lock_order_for_stock_mutation(order)
            locked_items = order_items if order_items is not None else get_locked_order_items(locked_order)
            ordered_items, locked_products, locked_sizes = lock_inventory_rows(locked_items)
            _mutate_inventory(
                locked_order,
                ordered_items=ordered_items,
                locked_products=locked_products,
                locked_sizes=locked_sizes,
                direction='restore',
            )
            return True

    except Exception as exc:
        logger.error(
            "Failed to restore stock | order_id=%s | user_id=%s | error=%s",
            order.id,
            order.user_id,
            exc,
        )
        return False


def ensure_paid_order_stock_reduced(order, save=True):
    """
    Ensure stock is reduced exactly once for a paid fulfillment order.
    """
    try:
        with transaction.atomic(savepoint=False):
            locked_order = get_locked_order(order)

            if locked_order.status not in PAID_FULFILLMENT_STATUSES or locked_order.payment_status != 'paid':
                return False

            if locked_order.stock_reduced:
                _hydrate_order_instance(order, locked_order)
                return False

            locked_items = get_locked_order_items(locked_order)
            if not locked_items:
                logger.info(
                    "Skipping stock reduction because order has no items | order_id=%s | user_id=%s",
                    locked_order.id,
                    locked_order.user_id,
                )
                return False

            reduce_stock(locked_order, order_items=locked_items)

            update_kwargs = {'stock_reduced': True}
            locked_order.stock_reduced = True
            if not locked_order.payment_confirmed_at:
                locked_order.payment_confirmed_at = timezone.now()
                update_kwargs['payment_confirmed_at'] = locked_order.payment_confirmed_at
            if locked_order.payment_retry_reserved_at:
                locked_order.payment_retry_reserved_at = None
                update_kwargs['payment_retry_reserved_at'] = None

            if save:
                Order.objects.filter(pk=locked_order.pk, stock_reduced=False).update(**update_kwargs)

            _hydrate_order_instance(order, locked_order)
            logger.info(
                "Stock reduced for manually processed paid order | order_id=%s | user_id=%s",
                locked_order.id,
                locked_order.user_id,
            )
            return True

    except Exception as exc:
        logger.error(
            "Failed to finalize stock reduction | order_id=%s | user_id=%s | error=%s",
            order.id,
            order.user_id,
            exc,
        )
        raise


def confirm_order_payment(order, payment_reference='', save=True):
    """
    Confirm order payment and reduce stock exactly once.
    """
    try:
        with transaction.atomic(savepoint=False):
            locked_order = get_locked_order(order)

            if (
                payment_reference
                and locked_order.razorpay_payment_id
                and locked_order.razorpay_payment_id != payment_reference
            ):
                raise ValueError(
                    f"Order {locked_order.id} is already linked to payment reference "
                    f"{locked_order.razorpay_payment_id}."
                )

            if locked_order.payment_status == 'paid':
                if locked_order.payment_retry_reserved_at is not None:
                    Order.objects.filter(pk=locked_order.pk).update(payment_retry_reserved_at=None)
                    locked_order.payment_retry_reserved_at = None
                logger.info(
                    "Order already paid, skipping confirmation | order_id=%s | user_id=%s",
                    locked_order.id,
                    locked_order.user_id,
                )
                _hydrate_order_instance(order, locked_order)
                return locked_order, False

            locked_items = get_locked_order_items(locked_order)
            now = timezone.now()
            update_fields = ['payment_status', 'status', 'payment_confirmed_at']
            locked_order.payment_status = 'paid'
            locked_order.status = 'paid'
            locked_order.payment_confirmed_at = now

            if payment_reference and not locked_order.razorpay_payment_id:
                locked_order.razorpay_payment_id = payment_reference
                update_fields.append('razorpay_payment_id')

            if locked_order.payment_retry_reserved_at is not None:
                locked_order.payment_retry_reserved_at = None
                update_fields.append('payment_retry_reserved_at')

            if not locked_order.stock_reduced:
                reduce_stock(locked_order, order_items=locked_items)
                locked_order.stock_reduced = True
                update_fields.append('stock_reduced')
            else:
                logger.info(
                    "Order stock already reduced, skipping mutation | order_id=%s | user_id=%s",
                    locked_order.id,
                    locked_order.user_id,
                )

            if save:
                locked_order.save(update_fields=update_fields)

            _hydrate_order_instance(order, locked_order)
            logger.info(
                "Order payment confirmed and stock reduced | order_id=%s | user_id=%s",
                locked_order.id,
                locked_order.user_id,
            )
            return locked_order, True

    except Exception as exc:
        logger.error(
            "Failed to confirm order | order_id=%s | user_id=%s | error=%s",
            order.id,
            order.user_id,
            exc,
        )
        raise
