# Email Fixes - Quick Reference

## Two Fixes Applied

### 1. Email Claim Blocking
**Problem**: Claims stuck forever, blocking emails
**Fix**: `FORCE_EMAIL_RETRY` setting auto-resets stuck claims

### 2. Async Task Never Executed
**Problem**: Task queued but Celery not running
**Fix**: Sync fallback always sends email

## Enable Force Retry
```bash
export FORCE_EMAIL_RETRY=true
```
Or in .env: `FORCE_EMAIL_RETRY=true`

## Monitor Logs
```bash
tail -f logs.log | grep "email_service\|signals"
```

Key patterns:
- `Email async queued: True` → Async OK
- `Email async queued: False` → Fallback to sync
- `FORCE RESET:` → Stuck claim reset
- `EMAIL CLAIM ->` → Email claimed

## Check Status
```python
from orders.models import Order

# Stuck claims
stuck = Order.objects.filter(
    confirmation_email_claimed_at__isnull=False,
    confirmation_email_sent=False
)

# Missing emails
pending = Order.objects.filter(
    status='confirmed',
    payment_status='paid',
    confirmation_email_sent=False
)
```

## Manual Reset
```python
# Single order
order = Order.objects.get(id=123)
order.confirmation_email_claimed_at = None
order.save()

# All stuck
Order.objects.filter(
    confirmation_email_claimed_at__isnull=False,
    confirmation_email_sent=False
).update(confirmation_email_claimed_at=None)
```

## Force Sync (No Async)
```bash
export ORDER_ASYNC_NOTIFICATIONS_ENABLED=false
```

## Test
```bash
python manage.py test orders.tests
python test_async_fallback.py
python demo_email_claim_fix.py
```

## Celery
```bash
# Start
celery -A syafra worker --loglevel=info

# Check status
celery -A syafra inspect stats
```

## Files Modified
- `syafra/settings.py`
- `orders/services/email_service.py`
- `orders/signals.py`

## Files Created
- `test_async_fallback.py`
- `test_email_claim_fix.py`
- `demo_email_claim_fix.py`
- `COMPLETE_EMAIL_FIX_SUMMARY.md`

## Result
✅ No email loss
✅ Works with/without Celery
✅ Self-healing
✅ Production ready
