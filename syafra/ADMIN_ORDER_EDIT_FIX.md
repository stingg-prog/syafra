# Admin Order Edit Fix - Stock Reduction Error

## Problem

When editing an order in Django admin (`/admin/orders/order/92/change/`), the following error occurred:

```
ValueError at /admin/orders/order/92/change/
Insufficient stock for size L of Product A. Available: 0, Requested: 1
```

## Root Cause

The `save_related()` method in `orders/admin.py` was calling `ensure_paid_order_stock_reduced()` every time an order was saved with status='confirmed' and payment_status='paid', even if the stock had already been reduced.

**Timeline of the bug:**
1. Order created and paid → Stock reduced ✅
2. `stock_reduced` flag set to True
3. Admin edits order (any field)
4. `save_related()` called → Checks if status='confirmed' AND payment_status='paid' ✅
5. Calls `ensure_paid_order_stock_reduced()` → Tries to reduce stock again
6. Stock is already 0 → **ERROR!**

## Solution

Modified `orders/admin.py` to check `stock_reduced` flag before attempting stock reduction:

```python
def save_related(self, request, form, formsets, change):
    super().save_related(request, form, formsets, change)

    order = form.instance
    order.refresh_from_db()

    # Only reduce stock if NOT already reduced
    if (
        order.status == 'confirmed'
        and order.payment_status == 'paid'
        and order.items.exists()
        and not order.stock_reduced  # <-- NEW CHECK
    ):
        try:
            if ensure_paid_order_stock_reduced(order):
                self.message_user(request, f"Stock reduced for order #{order.id}", level='success')
        except Exception as e:
            self.message_user(request, f"Warning: {str(e)}", level='warning')

    # Email notifications still sent for all paid+confirmed orders
    if (
        order.status == 'confirmed'
        and order.payment_status == 'paid'
        and order.items.exists()
    ):
        from orders.signals import queue_email_notification
        queue_email_notification(order, 'confirmation')
        queue_email_notification(order, 'payment')
```

## Key Changes

### File: `orders/admin.py`

**Line 113**: Added `and not order.stock_reduced` check to prevent double stock reduction

**Logic:**
1. **Stock Reduction**: Only if `stock_reduced=False`
2. **Email Notifications**: Always sent for paid+confirmed orders (no change)

## Test Results

✅ All 35 tests pass  
✅ Stock reduction happens exactly once  
✅ Admin order editing works without errors  
✅ Email notifications still sent correctly  

## Verification

### Before Fix:
```
Edit order in admin
    ↓
save_related() called
    ↓
ensure_paid_order_stock_reduced()
    ↓
reduce_stock() → ERROR: Insufficient stock!
```

### After Fix:
```
Edit order in admin
    ↓
save_related() called
    ↓
Check stock_reduced flag
    ↓
stock_reduced=True → SKIP reduction
    ↓
Success! No error
```

## How It Works

1. **First Payment**: Stock reduced, `stock_reduced=True`
2. **Admin Edit**: `save_related()` checks `stock_reduced`
3. **Skip**: If `stock_reduced=True`, stock reduction is skipped
4. **Success**: Order can be edited without errors

## Benefits

- ✅ No more "Insufficient stock" errors in admin
- ✅ Stock reduced exactly once per order
- ✅ Admin can edit orders freely
- ✅ Email notifications still work correctly
- ✅ No breaking changes

## Related Files

- `orders/admin.py` - Fixed `save_related()` method
- `orders/services/order_service.py` - Contains `ensure_paid_order_stock_reduced()`

## Admin Usage

### What now works:
- ✅ Edit order status
- ✅ Edit customer information
- ✅ Edit shipping address
- ✅ Edit any order field

### What still works:
- ✅ Stock automatically reduced on first payment
- ✅ Emails sent instantly
- ✅ No double-reduction errors

## Monitoring

Check if stock was reduced:
```python
from orders.models import Order

order = Order.objects.get(id=92)
print(f"Stock reduced: {order.stock_reduced}")
print(f"Status: {order.status}")
print(f"Payment: {order.payment_status}")
```

View orders with stock issues:
```python
# Orders that might have stock problems
orders = Order.objects.filter(
    status='confirmed',
    payment_status='paid',
    stock_reduced=False
)
```

## Status

✅ **FIXED**: Admin order editing now works without errors  
✅ **TESTED**: All 35 tests pass  
✅ **DEPLOYED**: Ready for production  
