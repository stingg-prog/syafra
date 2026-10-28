# Email Claim Fix - Quick Reference

## Problem
Confirmation emails stuck because claim system blocks execution when claim exists but email never sent.

## Solution
Added automatic claim reset mechanism with `FORCE_EMAIL_RETRY` setting.

## Quick Start

### Enable Force Retry
```bash
# Environment variable
export FORCE_EMAIL_RETRY=true

# Or in .env file
FORCE_EMAIL_RETRY=true

# Or in settings.py
FORCE_EMAIL_RETRY = True
```

### Monitor Logs
```bash
# Watch email service logs
tail -f logs.log | grep "email_service"

# Look for these patterns:
# - "EMAIL CLAIM ->" - Successful claim
# - "Email claim blocked" - Blocked claim
# - "FORCE RESET:" - Auto-reset
```

## Check for Stuck Claims
```python
from orders.models import Order

# Find stuck orders
stuck = Order.objects.filter(
    confirmation_email_claimed_at__isnull=False,
    confirmation_email_sent=False
)
print(f"Stuck orders: {stuck.count()}")
```

## Manual Fix
```python
# Reset single order
order = Order.objects.get(id=123)
order.confirmation_email_claimed_at = None
order.save()

# Reset all stuck orders
Order.objects.filter(
    confirmation_email_claimed_at__isnull=False,
    confirmation_email_sent=False
).update(confirmation_email_claimed_at=None)
```

## Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `FORCE_EMAIL_RETRY` | `False` | Auto-reset stuck claims |
| `ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS` | `900` | Claim expiry (15 min) |

## Test
```bash
python manage.py test orders.tests.OrderFlowTest
python demo_email_claim_fix.py
```

## Files Changed
- `syafra/settings.py` - Added FORCE_EMAIL_RETRY setting
- `orders/services/email_service.py` - Enhanced claim logic

## Support
Check `IMPLEMENTATION_REPORT.md` for detailed documentation.
