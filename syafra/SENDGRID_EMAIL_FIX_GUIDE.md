# STEP 1: ROOT CAUSE ANALYSIS

## Why SendGrid Emails Are Not Being Delivered

| # | Root Cause | How to Fix |
|---|------------|------------|
| 1 | **EMAIL_SERVICE not set on Render** | Set `EMAIL_SERVICE=sendgrid` in Render environment |
| 2 | **SENDGRID_API_KEY missing** | Set actual SendGrid API key in Render |
| 3 | **DEFAULT_FROM_EMAIL not verified** | Use a verified sender in SendGrid |
| 4 | **Console backend fallback** | Remove ALLOW_CONSOLE_EMAIL_IN_PRODUCTION |
| 5 | **DOMAIN misconfigured** | Set DOMAIN to your actual Render hostname |
| 6 | **DEBUG=True on Render** | Ensure DEBUG=false in production |
| 7 | **Missing EMAIL_USE_TLS** | Already configured, just needs env vars |

---

# STEP 2: SENDGRID SETTINGS.PY CONFIGURATION

The current settings.py already has correct SendGrid config. The issue is **environment variables not set on Render**.

## Required Render Environment Variables

```
EMAIL_SERVICE=sendgrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_SENDER_EMAIL=your-verified@domain.com
DEFAULT_FROM_EMAIL=SYAFRA <your-verified@domain.com>
DOMAIN=syafra.onrender.com
USE_HTTPS=True
DEBUG=false
```

---

# STEP 3: ORDER CONFIRMATION EMAIL FIX

## Current Implementation (Already Working)

```python
# orders/signals.py - post_save handler
@receiver(post_save, sender=Order)
def handle_order_notifications(sender, instance, created, **kwargs):
    if created:
        queue_email_notification(instance, 'confirmation')
```

## Verify Email Service is Called

```python
# Test by creating an order and checking logs
# Should see: EMAIL SENT INSTANTLY | type=confirmation | order=X
```

---

# STEP 4: ORDER STATUS UPDATE EMAIL FIX

Status updates are triggered in `handle_order_notifications()`:

```python
if new_status == 'confirmed':
    queue_email_notification(instance, 'status', status_override='confirmed')
elif new_status == 'processing':
    queue_email_notification(instance, 'status', status_override='processing')
elif new_status == 'shipped':
    queue_email_notification(instance, 'status', status_override='shipped')
elif new_status == 'delivered':
    queue_email_notification(instance, 'status', status_override='delivered')
```

---

# STEP 5: PASSWORD RESET EMAIL FIX

## Check 1: URL Configuration

```python
# accounts/urls.py
path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
```

## Check 2: Email Backend

Password reset uses Django's built-in `PasswordResetView` which calls `send_mail()` internally. As long as EMAIL_BACKEND is SMTP, it works.

## Check 3: DOMAIN Setting

```python
# settings.py
DOMAIN = os.environ.get("DOMAIN", "127.0.0.1:8000")
```

On Render, this MUST be set to your actual hostname.

---

# STEP 6: DEBUGGING & LOGGING SETUP

## Current Logging (Already Configured)

```python
# settings.py
'django.core.mail': {
    'handlers': ['console'],
    'level': 'DEBUG' if DEBUG else 'INFO',
    'propagate': False,
},
```

## Add Email Debug View

Create `debug_email_view.py`:

```python
# debug_email_view.py
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def test_email_api(request):
    """Debug endpoint to test email sending."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    recipient = request.POST.get('email', '')
    if not recipient:
        return JsonResponse({'error': 'Email required'}, status=400)
    
    result = {
        'backend': settings.EMAIL_BACKEND,
        'host': getattr(settings, 'EMAIL_HOST', 'N/A'),
        'port': getattr(settings, 'EMAIL_PORT', 'N/A'),
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'domain': settings.DOMAIN,
    }
    
    try:
        send_mail(
            subject='Test Email from SYAFRA',
            message='This is a test email.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        result['status'] = 'sent'
        logger.info(f"Test email sent to {recipient}")
    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)
        logger.error(f"Test email failed: {e}")
    
    return JsonResponse(result)
```

---

# STEP 7: TEST COMMANDS

## Local Test

```bash
# Set environment variables
$env:EMAIL_SERVICE="sendgrid"
$env:SENDGRID_API_KEY="SG.your_key"
$env:DEFAULT_FROM_EMAIL="SYAFRA <test@yourdomain.com>"
$env:DOMAIN="localhost:8000"

# Run test script
python test_email.py --to=your@email.com
```

## Django Shell Test

```bash
python manage.py shell

>>> from django.conf import settings
>>> print(f"Backend: {settings.EMAIL_BACKEND}")
>>> print(f"Host: {settings.EMAIL_HOST}")
>>> print(f"Domain: {settings.DOMAIN}")

>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Body', settings.DEFAULT_FROM_EMAIL, ['your@email.com'], fail_silently=False)
```

## Check Logs on Render

1. Go to Render Dashboard → Your App → Logs
2. Look for: `EMAIL SENT SUCCESS` or `EMAIL SEND FAILED`

---

# STEP 8: FINAL CHECKLIST FOR ZERO-DELAY EMAIL DELIVERY

| # | Checklist Item | Status |
|---|----------------|--------|
| 1 | EMAIL_SERVICE=sendgrid set on Render | [ ] |
| 2 | SENDGRID_API_KEY set on Render | [ ] |
| 3 | SENDGRID_SENDER_EMAIL verified in SendGrid | [ ] |
| 4 | DEFAULT_FROM_EMAIL set on Render | [ ] |
| 5 | DOMAIN=syafra.onrender.com set on Render | [ ] |
| 6 | USE_HTTPS=True set on Render | [ ] |
| 7 | DEBUG=false set on Render | [ ] |
| 8 | ALLOW_CONSOLE_EMAIL_IN_PRODUCTION NOT set | [ ] |
| 9 | Celery NOT required (sync emails) | [ ] |
| 10 | transaction.on_commit delay removed | [x] |

---

# QUICK FIX COMMAND

Run this to set environment variables locally (PowerShell):

```powershell
$env:EMAIL_SERVICE="sendgrid"
$env:SENDGRID_API_KEY="SG.your_actual_key_here"
$env:DEFAULT_FROM_EMAIL="SYAFRA <your@domain.com>"
$env:DOMAIN="syafra.onrender.com"
$env:USE_HTTPS="true"
```

Then test:

```bash
python test_email.py --to=your@email.com
```

---

# SENDGRID SETUP STEPS

1. Create SendGrid account at sendgrid.com
2. Go to Settings → API Keys → Create API Key
3. Copy the key (starts with SG.)
4. Go to Settings → Sender Authentication
5. Verify a single sender or domain
6. Add environment variables to Render
7. Test with the script above

---

# VERIFY SENDGRID ON RENDER

Check Render logs after deploying:

```
[EMAIL CONFIG] backend=django.core.mail.backends.smtp.EmailBackend 
host=smtp.sendgrid.net port=587 from=SYAFRA <noreply@yourdomain.com> service=sendgrid
```

If you see `console.EmailBackend`, the environment variables are not set.
