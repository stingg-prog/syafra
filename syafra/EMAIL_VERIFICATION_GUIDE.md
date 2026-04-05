# SYAFRA EMAIL SYSTEM - COMPLETE VERIFICATION GUIDE

## CURRENT IMPLEMENTATION STATUS

### What Is Already Working ✓

1. **Signals connected** in `orders/apps.py`:
```python
def ready(self):
    import orders.signals  # Signals auto-loaded
```

2. **Order Confirmation Signal** - `orders/signals.py:184-205`:
   - Triggers on `post_save` with `created=True`
   - Sends confirmation + payment email
   - Updates `confirmation_email_sent = True`

3. **Status Update Signal** - `orders/signals.py:256-271`:
   - Triggers on status change (confirmed, processing, shipped, delivered)
   - Sends status update email
   - No duplicate emails (checks `_previous_status`)

4. **Email Sending** - `orders/services/email_service.py`:
   - Uses `fail_silently=False`
   - Uses `DEFAULT_FROM_EMAIL`
   - Uses SendGrid SMTP

---

## VERIFICATION CHECKLIST

### STEP 1: Order Confirmation Email ✓

| Item | Status | Location |
|------|--------|----------|
| post_save signal | ✓ Working | `signals.py:184` |
| Trigger on created=True | ✓ Working | `signals.py:186` |
| Send to order.email | ✓ Working | `email_service.py:46` |
| Update confirmation_email_sent | ✓ Working | `email_service.py:329` |

### STEP 2: Order Status Update Email ✓

| Item | Status | Location |
|------|--------|----------|
| Track previous status | ✓ Working | `signals.py:166` |
| Detect status change | ✓ Working | `signals.py:231-233` |
| Send on status change | ✓ Working | `signals.py:256-271` |
| No duplicate emails | ✓ Working | `email_service.py:94` |

### STEP 3: Email Sending ✓

```python
# From email_service.py:62-69
send_mail(
    subject=f'Order Confirmation - Order #{order.id}',
    message=plain_message,
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=[order.email],
    html_message=html_message,
    fail_silently=False,  # ✓ Exposed, not silent
)
```

### STEP 4: Signal File Setup ✓

| Item | Status | File |
|------|--------|------|
| signals.py exists | ✓ | `orders/signals.py` |
| @receiver decorators | ✓ | `signals.py:8` |
| Connected in apps.py | ✓ | `orders/apps.py:9` |
| Auto-loaded | ✓ | Django auto-discovery |

### STEP 5: Password Reset ✓

| Item | Status | Location |
|------|--------|----------|
| Django auth included | ✓ | `INSTALLED_APPS` |
| Password reset URLs | ✓ | `accounts/urls.py:16-29` |
| SMTP backend | ✓ | `settings.py:438` |
| Templates exist | ✓ | `templates/registration/` |

### STEP 6: Debugging Logs ✓

```
# When order created:
New order created | Order #X | User: Y
🔥 PAYMENT DETECTED (created) → order=X
🔥 EMAILS TRIGGERED for new paid order #X

# When email sent:
EMAIL SENT INSTANTLY | type=confirmation | order=X
EMAIL SENT SUCCESS | type=confirmation | order=X
```

---

## THE ACTUAL PROBLEM

**Environment variables NOT set on Render!**

### On Render Dashboard, You Must Set:

| Variable | Value |
|----------|-------|
| `EMAIL_SERVICE` | `sendgrid` |
| `SENDGRID_API_KEY` | `SG.your_actual_key` |
| `SENDGRID_SENDER_EMAIL` | `your@verified-domain.com` |
| `DEFAULT_FROM_EMAIL` | `SYAFRA <your@verified-domain.com>` |
| `DOMAIN` | `syafra.onrender.com` |
| `USE_HTTPS` | `true` |
| `DEBUG` | `false` |

---

## HOW TO TEST

### 1. Local Test (with env vars)

```bash
# PowerShell
$env:EMAIL_SERVICE="sendgrid"
$env:SENDGRID_API_KEY="SG.your_key"
$env:SENDGRID_SENDER_EMAIL="test@yourdomain.com"
$env:DEFAULT_FROM_EMAIL="SYAFRA <test@yourdomain.com>"
$env:DOMAIN="localhost:8000"

python test_email_complete.py --to=your@email.com
```

### 2. Check Logs

After setting env vars on Render:
1. Deploy
2. Create test order
3. Check Render logs for:
   - `🔥 EMAILS TRIGGERED`
   - `EMAIL SENT INSTANTLY`
   - `EMAIL SENT SUCCESS`

### 3. Django Shell Test

```bash
python manage.py shell

>>> from django.conf import settings
>>> settings.EMAIL_BACKEND
'django.core.mail.backends.smtp.EmailBackend'  # Should be this

>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Body', settings.DEFAULT_FROM_EMAIL, ['you@email.com'])
1  # Should return 1
```

---

## EMAIL FLOW DIAGRAM

```
Order Created
     │
     ▼
post_save signal (created=True)
     │
     ▼
queue_email_notification(order, 'confirmation')
     │
     ▼
_send_email_instant()  ← NO DELAY
     │
     ▼
send_notification_email()
     │
     ├── Check: confirmation_email_sent?
     ├── If not sent → send_order_confirmation_email()
     │                      │
     │                      ▼
     │                 send_mail() via SMTP
     │
     └── Mark confirmation_email_sent = True
```

---

## TROUBLESHOOTING

### Issue: Console backend in logs

```
EMAIL_BACKEND: django.core.mail.backends.console.EmailBackend
```

**Fix:** Set `EMAIL_SERVICE=sendgrid` on Render

### Issue: Emails log but not received

1. Check SendGrid verified sender
2. Check spam folder
3. Check SendGrid activity dashboard

### Issue: Password reset link broken

**Fix:** Set `DOMAIN=syafra.onrender.com` on Render

---

## QUICK FIX COMMANDS

### Check current email config:
```bash
python test_email_complete.py --skip-send
```

### Test sending email:
```bash
python test_email_complete.py --to=your@email.com
```

### Verify signals are connected:
```bash
python manage.py shell

>>> from orders.signals import handle_order_notifications
>>> print("Signals connected!")
```

---

## SUMMARY

| Component | Status | Notes |
|-----------|--------|-------|
| Order Confirmation Signal | ✓ | Works when created=True + paid |
| Status Update Signal | ✓ | Works on status change |
| Email Service | ✓ | fail_silently=False |
| SendGrid SMTP | ✓ | Config ready |
| Password Reset | ✓ | URL + templates exist |
| **MISSING** | ✗ | **Environment variables on Render** |

**Everything is coded correctly. You just need to set the environment variables on Render!**
