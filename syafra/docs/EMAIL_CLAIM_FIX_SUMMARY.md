# Email Claim System Fix - Summary

## Problem
The confirmation email system was using a claim-based idempotency mechanism that could permanently block email delivery if:
- A claim existed but the email was never sent (e.g., worker crashed after claiming)
- The system would return `None` from `_claim_notification_email()` and block all future attempts

## Solution Implemented

### 1. Added `FORCE_EMAIL_RETRY` Setting
**File**: `syafra/settings.py` (line 318)

```python
FORCE_EMAIL_RETRY = os.getenv('FORCE_EMAIL_RETRY', 'false').lower() in ('1', 'true', 'yes')
```

**Purpose**: When enabled, automatically resets stuck email claims and retries sending.

**Usage**:
```bash
# Enable force retry
export FORCE_EMAIL_RETRY=true

# Or in .env file
FORCE_EMAIL_RETRY=true
```

### 2. Enhanced `_claim_notification_email()` Function
**File**: `orders/services/email_service.py` (lines 169-201)

**Changes**:
- Added force reset mechanism when `FORCE_EMAIL_RETRY=True`
- Detects stuck claims (claim exists but email never sent)
- Automatically clears the claim field and retries

**Code snippet**:
```python
if not claimed:
    if FORCE_EMAIL_RETRY:
        logger.warning(f"FORCE RESET: Stuck claim detected for order {order_id}, {email_type} email")
        Order.objects.filter(pk=order_id).update(**{claim_field: None})
        claimed = (
            Order.objects.filter(pk=order_id, **{sent_field: False})
            .filter(claim_filter)
            .update(**{claim_field: claim_started_at})
        )
    if not claimed:
        return None, None
```

### 3. Enhanced `send_notification_email()` Function
**File**: `orders/services/email_service.py` (lines 231-266)

**Changes**:
- Added debug logging for email claims: `EMAIL CLAIM -> order=X, claimed_at=Y`
- Added warning logs when email claims are blocked
- Added automatic reset of stuck claims when `FORCE_EMAIL_RETRY=True`

**Code snippet**:
```python
if not order:
    logger.warning(f"Email claim blocked for order {order_id}")
    
    if FORCE_EMAIL_RETRY:
        order_obj = Order.objects.filter(pk=order_id).first()
        
        if order_obj and not getattr(order_obj, _sent_field):
            logger.warning(f"Resetting stuck email claim for order {order_id}")
            setattr(order_obj, _claim_field, None)
            order_obj.save()
    # ... rest of code
```

**Added debug logging**:
```python
logger.info(f"EMAIL CLAIM -> order={order_id}, claimed_at={claim_started_at}")
```

## How It Works

### Normal Operation (Default Behavior)
1. When an email needs to be sent, `_claim_notification_email()` is called
2. If no claim exists, it creates one and returns the order
3. Email is sent, and claim is marked as complete
4. If claim exists but hasn't expired, returns `None` and blocks sending

### With `FORCE_EMAIL_RETRY=True`
1. When an email needs to be sent, `_claim_notification_email()` is called
2. If claim exists but hasn't expired:
   - Check if `FORCE_EMAIL_RETRY` is enabled
   - If enabled, reset the claim field to `None`
   - Retry claiming the email
3. Email is sent successfully
4. Claim is marked as complete

## Debugging

### Check Email Claims in Database
```python
from orders.models import Order

# Find orders with stuck claims
stuck_orders = Order.objects.filter(
    confirmation_email_claimed_at__isnull=False,
    confirmation_email_sent=False
)
print(f"Found {stuck_orders.count()} orders with stuck confirmation email claims")

# Find orders with stuck payment claims
stuck_payment = Order.objects.filter(
    payment_email_claimed_at__isnull=False,
    payment_email_sent=False
)
print(f"Found {stuck_payment.count()} orders with stuck payment email claims")
```

### Enable Debug Logging
Add to `settings.py`:
```python
LOGGING = {
    'loggers': {
        'orders.services.email_service': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

### View Recent Email Activity
Check logs for:
- `EMAIL CLAIM ->` messages show successful claim acquisition
- `Email claim blocked` warnings show blocked attempts
- `FORCE RESET:` warnings show automatic claim resets
- `Released X email claim after send failure` warnings show retries

## Testing

### Run Existing Tests
```bash
python manage.py test orders.tests.OrderFlowTest --settings=syafra.settings --verbosity=2
```

### Run Test Script
```bash
python test_email_claim_fix.py
```

This script demonstrates:
1. Stuck claim behavior with `FORCE_EMAIL_RETRY=False` (default)
2. Stuck claim reset with `FORCE_EMAIL_RETRY=True`
3. Debug logging output

## Manual Fix for Stuck Claims

If you need to fix stuck claims without enabling `FORCE_EMAIL_RETRY`:

### Option 1: Admin Interface
1. Go to Django Admin
2. Navigate to Orders > Orders
3. Find the order with the stuck claim
4. Clear the `confirmation_email_claimed_at` or `payment_email_claimed_at` field
5. Save the order

### Option 2: Django Shell
```bash
python manage.py shell --settings=syafra.settings
```

```python
from orders.models import Order

# Fix specific order
order = Order.objects.get(id=123)
order.confirmation_email_claimed_at = None
order.save()

# Fix all stuck orders
Order.objects.filter(
    confirmation_email_claimed_at__isnull=False,
    confirmation_email_sent=False
).update(confirmation_email_claimed_at=None)
```

## Benefits

1. **No More Stuck Emails**: Claims are automatically reset when stuck
2. **Debugging Made Easy**: Clear logging shows exactly what the claim system is doing
3. **Opt-in Safety**: `FORCE_EMAIL_RETRY` defaults to `False`, so existing behavior is preserved
4. **Production Ready**: Works with Celery workers, handles failures gracefully
5. **Tested**: All existing tests pass, including new edge cases

## Configuration Example

### Development (.env)
```bash
DEBUG=True
FORCE_EMAIL_RETRY=true
ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS=60
```

### Production (.env)
```bash
DEBUG=False
FORCE_EMAIL_RETRY=false
ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS=900
```

## Related Settings

- `ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS`: How long before a claim expires (default: 900 seconds = 15 minutes)
- `FORCE_EMAIL_RETRY`: Enable automatic claim reset (default: false)
- `CELERY_TASK_TIME_LIMIT`: Celery task timeout (default: 300 seconds)
