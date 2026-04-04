# Password Reset Email - Troubleshooting Guide

## Problem
Users are NOT receiving password reset emails.

## Root Cause Identified
Your application is running in **DEBUG=True** mode with **console email backend**, which means:
- Emails are printed to the terminal/console
- Emails are NOT sent to actual inbox

## Current Configuration
```python
DEBUG = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## Solution Options

### Option 1: Development Testing (Current Setup)
Emails will print to terminal. To test:
```bash
# Trigger password reset in browser, then check your terminal
# You'll see the email content printed there
```

### Option 2: Use Mailtrap for Testing (Recommended)
Free service that captures emails without sending to real inbox.

1. Create account at https://mailtrap.io
2. Get your credentials from inbox settings
3. Update your `.env` file:
```bash
EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST='smtp.mailtrap.io'
EMAIL_PORT=2525
EMAIL_HOST_USER='your-mailtrap-username'
EMAIL_HOST_PASSWORD='your-mailtrap-password'
EMAIL_USE_TLS=True
```

### Option 3: Production Setup with Gmail
**⚠️ Requires Gmail App Password, NOT regular password**

1. Enable 2-Factor Authentication on your Google account
2. Generate App Password at: https://myaccount.google.com/apppasswords
3. Update your `.env` file:
```bash
DEBUG=False
EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST='smtp.gmail.com'
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER='your-email@gmail.com'
EMAIL_HOST_PASSWORD='your-16-character-app-password'
DEFAULT_FROM_EMAIL='noreply@yourdomain.com'
```

## Testing

### Run Diagnostic Test
```bash
python test_email_config.py
```

### Manual Test
```bash
python manage.py shell
```

Then:
```python
from accounts.utils.email import test_email_configuration, send_test_email
import json

# Show configuration
print(json.dumps(test_email_configuration(), indent=2))

# Send test email
send_test_email('your-email@example.com')
```

## Files Modified

### 1. `accounts/utils/email.py`
- Enhanced with better error handling
- Added `send_password_reset_email()` function
- Added `test_email_configuration()` diagnostic function
- Added `send_test_email()` function
- Uses `EmailMultiAlternatives` for HTML emails

### 2. `templates/registration/password_reset_email.html`
- Improved HTML email template
- Added responsive design
- Clear call-to-action button
- Fallback plain text link

### 3. `test_email_config.py` (New)
- Interactive diagnostic script
- Tests email sending
- Tests password reset flow
- Shows troubleshooting guide

## Verification Checklist

- [ ] Check terminal for printed emails (if DEBUG=True)
- [ ] Check spam/junk folder
- [ ] Verify user email exists in database
- [ ] Verify user account is active
- [ ] Check email template renders correctly
- [ ] Test with different email providers

## Common Issues

### 1. "SMTPAuthenticationError: Username and Password not accepted"
- ✅ Use App Password, not regular password (for Gmail)
- ✅ Check EMAIL_HOST_USER is correct
- ✅ Enable 2FA and generate App Password

### 2. "Connection refused" or timeout
- ✅ Check firewall settings
- ✅ Verify correct port (587 for TLS, 465 for SSL)
- ✅ Try different network (disable VPN)

### 3. Emails going to spam
- ✅ Add sender to contacts
- ✅ Check spam filters
- ✅ Use proper FROM email address
- ✅ Consider SPF/DKIM setup for production

### 4. Template not rendering
- ✅ Verify template file exists at correct path
- ✅ Check template syntax
- ✅ Ensure context variables are passed

## Next Steps

1. **For Development**: Monitor terminal for printed emails
2. **For Testing**: Use Mailtrap.io
3. **For Production**: Configure Gmail App Password or use dedicated SMTP service

## Production Recommendations

- Use services like SendGrid, Mailgun, or AWS SES
- Set up SPF, DKIM, and DMARC records
- Monitor email deliverability
- Set up email error monitoring
- Consider using Celery for async email sending

## Support

If issues persist after following this guide:
1. Run `python test_email_config.py`
2. Share the output
3. Check server logs for specific errors
4. Verify network connectivity to SMTP server
