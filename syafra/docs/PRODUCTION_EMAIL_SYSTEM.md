# Production-Grade Email System - Complete Guide

## Problem Analysis

### Current Issue: Inconsistent Email Delivery

**Symptoms:**
- Emails received on mobile but not on laptop
- Delayed delivery
- Emails going to spam
- Different behavior across devices

**Root Cause:**
Using personal Gmail SMTP for transactional emails is NOT recommended for production:
- Gmail has strict rate limits (500 emails/day for regular accounts)
- Gmail flags emails from non-verified domains
- Gmail spam filters are aggressive
- Personal Gmail accounts are not meant for transactional emails

## Solution: Transactional Email Service

### Recommended: SendGrid

**Why SendGrid:**
- Designed for transactional emails
- High deliverability (99%)
- 100 emails/day free tier
- Proper authentication (SPF, DKIM, DMARC)
- Detailed analytics
- Webhook support for tracking

### Alternative: Mailgun

**Why Mailgun:**
- 5,000 emails/month free
- Good deliverability
- Easy setup
- Developer-friendly API

## Configuration

### Option 1: SendGrid (Recommended)

#### Step 1: Create SendGrid Account
1. Go to: https://sendgrid.com
2. Sign up for free account
3. Verify your domain (recommended)
4. Create API Key

#### Step 2: Update .env File
```bash
# Email Service Configuration
EMAIL_SERVICE=sendgrid
SENDGRID_API_KEY=SG.your-api-key-here
DOMAIN=yourdomain.com

# Sender Identity
DEFAULT_FROM_EMAIL=SYAFRA <noreply@yourdomain.com>
```

#### Step 3: Install SendGrid
```bash
pip install sendgrid-django
```

#### Step 4: Verify Domain (Optional but Recommended)
1. In SendGrid dashboard, go to Settings > Sender Authentication
2. Add your domain (e.g., yourdomain.com)
3. Add DNS records provided by SendGrid:
   - SPF Record
   - DKIM Record
   - MX Record (if using SendGrid for receiving)

### Option 2: Gmail (Development Only)

**NOT RECOMMENDED FOR PRODUCTION** but can work for development.

#### Setup:
```bash
# .env file
EMAIL_SERVICE=gmail
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=SYAFRA <your-email@gmail.com>
DOMAIN=127.0.0.1:8000
```

#### Important: Create App Password
1. Enable 2-Factor Authentication on Gmail
2. Go to: https://myaccount.google.com/apppasswords
3. Generate App Password (16 characters)
4. Use this password, NOT your regular password

### Option 3: Mailgun (Alternative)

```bash
# .env file
EMAIL_SERVICE=mailgun
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=yourdomain.mailgun.org
DEFAULT_FROM_EMAIL=SYAFRA <noreply@yourdomain.com>
DOMAIN=yourdomain.com
```

## Current Configuration (settings.py)

The project now supports multiple email services:

```python
# Email Service Configuration
EMAIL_SERVICE = 'sendgrid'  # Options: 'sendgrid', 'gmail', 'mailgun'

# Domain for password reset links
DOMAIN = 'yourdomain.com'
```

## Email Deliverability Best Practices

### 1. Domain Authentication

**SPF Record:**
```
v=spf1 include:sendgrid.net ~all
```

**DKIM Record:**
Add the DKIM record provided by SendGrid/Mailgun

**DMARC Record:**
```
v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com
```

### 2. Email Content Best Practices

**Do:**
- ✅ Use consistent sender name
- ✅ Include clear subject lines
- ✅ Use HTML + plain text
- ✅ Add footer with physical address
- ✅ Make it easy to unsubscribe
- ✅ Test on multiple clients

**Don't:**
- ❌ Use spam trigger words ("FREE", "ACT NOW", "LIMITED TIME")
- ❌ Use excessive punctuation ("!!!", "???")
- ❌ Use all caps in subject
- ❌ Send attachments
- ❌ Use deceptive subject lines

### 3. Our Branded Email Template

The password reset email includes:
- ✅ Professional SYAFRA branding
- ✅ Clear call-to-action
- ✅ Fallback link for email clients that block buttons
- ✅ Expiration notice
- ✅ Security disclaimer
- ✅ Footer with brand name

### 4. Monitoring & Logging

Email logging is now configured:

```python
'django.core.mail': {
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}
```

Check logs for:
- Email send attempts
- Delivery status
- Errors

## Troubleshooting Email Delivery

### Issue 1: Email Not Received

**Check in order:**

1. **Spam/Junk folder** (Most common!)
2. **All mail/Archive**
3. **Gmail tabs** (Promotions, Social, Updates)
4. **Search** for "from:syafra"

**If in spam:**
- Mark as "Not Spam"
- Add to contacts
- Create filter to never mark as spam

### Issue 2: Email Delayed

**Possible causes:**
- Email service rate limiting
- Network issues
- Spam filtering

**Solution:**
- Use SendGrid for production
- Increase timeout in settings.py
- Check email service status page

### Issue 3: Different Devices Different Behavior

**Root cause:** Email client synchronization issues

**Solution:**
1. Clear cache on web email
2. Force sync on mobile
3. Use dedicated email app
4. Check same email account on all devices

### Issue 4: Spam Filter

**Prevention:**
1. Authenticate domain (SPF, DKIM)
2. Use consistent sender address
3. Avoid spam trigger words
4. Build sender reputation gradually
5. Monitor bounce rates

## Testing Email Delivery

### Test Script

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

# Send test email
result = send_mail(
    subject='Test Email - SYAFRA',
    message='This is a test email to verify email delivery.',
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=['your-email@example.com'],
    fail_silently=False
)

print(f'Email sent: {result}')
```

### Check Email Headers

Email headers reveal delivery path:
- `X-Mailer`: Shows our custom header
- `Received`: Shows servers the email passed through
- `Authentication-Results`: Shows SPF/DKIM status

## Migration Checklist

### Before Switching to SendGrid

- [ ] Create SendGrid account
- [ ] Verify domain (recommended)
- [ ] Create API key
- [ ] Install sendgrid-django: `pip install sendgrid-django`
- [ ] Update .env file
- [ ] Test email sending
- [ ] Verify deliverability
- [ ] Monitor for errors

### After Switching

- [ ] Test password reset flow
- [ ] Check spam folders
- [ ] Verify on multiple devices
- [ ] Monitor delivery logs
- [ ] Check email analytics in SendGrid

## Quick Reference

### Environment Variables

```bash
# Email Service
EMAIL_SERVICE=sendgrid  # or 'gmail' or 'mailgun'

# SendGrid
SENDGRID_API_KEY=SG.your-key

# Domain
DOMAIN=yourdomain.com

# From Email
DEFAULT_FROM_EMAIL=SYAFRA <noreply@yourdomain.com>

# Gmail (if using)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Mailgun (if using)
MAILGUN_API_KEY=your-key
MAILGUN_DOMAIN=your-domain.mailgun.org
```

### Password Reset URLs

| URL | Purpose |
|-----|---------|
| `/accounts/password-reset/` | Request reset |
| `/accounts/password-reset/done/` | Email sent |
| `/accounts/reset/<uid>/<token>/` | Set new password |
| `/accounts/reset/done/` | Complete |

## Summary

**Problem:** Gmail SMTP is unreliable for production

**Solution:** Use SendGrid (recommended)

**Benefits:**
- ✅ 99% deliverability
- ✅ Professional reputation
- ✅ Analytics & tracking
- ✅ No rate limits
- ✅ Proper authentication

**Next Steps:**
1. Create SendGrid account
2. Get API key
3. Update .env
4. Test email sending
5. Verify delivery on all devices

## Support

### SendGrid Resources
- Documentation: https://docs.sendgrid.com
- Support: https://support.sendgrid.com
- API Reference: https://docs.sendgrid.com/api-reference

### Common Issues

**"Email goes to spam"**
→ Authenticate domain, use consistent sender

**"Rate limit exceeded"**
→ Use SendGrid, has higher limits

**"Different on mobile vs laptop"**
→ Check email client sync, not Django issue

**"Emails delayed"**
→ Use SendGrid, check network, increase timeout

---

**Status:** Production-ready configuration available  
**Recommendation:** Switch to SendGrid for reliable email delivery  
**Current:** Gmail works but not recommended for production
