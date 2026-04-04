# SendGrid Email Setup Guide

## Quick Setup (5 minutes)

### Step 1: Create SendGrid Account

1. Go to: https://signup.sendgrid.com
2. Choose "Free Plan" (100 emails/day)
3. Verify your email
4. Complete onboarding

### Step 2: Create API Key

1. Log in to SendGrid: https://app.sendgrid.com
2. Go to: Settings → API Keys
3. Click "Create API Key"
4. Name: "SYAFRA Django"
5. API Key Permission: "Full Access"
6. Click "Create & View"
7. **COPY THE API KEY** (starts with `SG.`)

### Step 3: Verify Sender (Required)

**Option A: Single Sender Verification (Quick)**

1. Go to: Settings → Sender Authentication
2. Click "Verify a Single Sender"
3. Fill in:
   - From Email: `noreply@yourdomain.com`
   - From Name: `SYAFRA`
   - Reply Email: same as From Email
4. Click "Create"
5. Check your email and click verification link

**Option B: Domain Authentication (Recommended)**

1. Go to: Settings → Sender Authentication
2. Click "Authenticate Your Domain"
3. Enter: `yourdomain.com`
4. Click "Next"
5. Add the DNS records shown (SPF, DKIM)
6. Wait for verification (5 min - 48 hours)

### Step 4: Update .env File

Create/Edit `C:\Users\USER\syafra_store\syafra\.env`:

```env
# Email Configuration - SendGrid
EMAIL_SERVICE=sendgrid
SENDGRID_API_KEY=SG.your-api-key-here
SENDGRID_SENDER_EMAIL=noreply@yourdomain.com
DOMAIN=yourdomain.com

# For development, use console backend:
# EMAIL_SERVICE=console
```

**Important:** Replace `SG.your-api-key-here` with your actual SendGrid API key!

### Step 5: Restart Django Server

```bash
python manage.py runserver
```

## Testing

### Test Email Sending

```python
python manage.py shell
```

```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    'SendGrid Test',
    'SendGrid is working!',
    settings.DEFAULT_FROM_EMAIL,
    ['your-verified-email@gmail.com'],
    fail_silently=False
)
print("Email sent!")
```

### Test Password Reset

1. Go to: http://127.0.0.1:8000/accounts/password-reset/
2. Enter: `admin@example.com`
3. Check inbox (and spam)
4. Click reset link

## DNS Records (Domain Authentication)

If using domain authentication, add these records:

### SPF Record
```
TXT @ v=spf1 include:sendgrid.net ~all
```

### DKIM Record
```
CNAME mail._domainkey TXT "k=rsa; p=your-dkim-key"
```

**Where to add:**
- Go to your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.)
- Find DNS settings
- Add the records shown in SendGrid

## Troubleshooting

### "API Key not valid"
- Double-check the API key (starts with `SG.`)
- Make sure full key is copied
- Regenerate key if needed

### "Sender not verified"
- Complete sender verification
- Use verified email in `SENDGRID_SENDER_EMAIL`
- Check verification email

### "Domain not authenticated"
- Add SPF and DKIM records
- Wait 5-48 hours for DNS propagation
- Use single sender as workaround

### "Rate limit exceeded"
- Free plan: 100 emails/day
- Upgrade to paid plan for more
- Monitor usage in SendGrid dashboard

## Complete .env Example

```env
# Django Settings
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email - SendGrid
EMAIL_SERVICE=sendgrid
SENDGRID_API_KEY=SG.your-real-api-key-here
SENDGRID_SENDER_EMAIL=noreply@yourdomain.com
DOMAIN=localhost:8000

# For production:
# DEBUG=False
# DOMAIN=yourdomain.com
```

## SendGrid Dashboard

### Useful Links

- Dashboard: https://app.sendgrid.com
- API Keys: Settings → API Keys
- Sender Auth: Settings → Sender Authentication
- Email Activity: Activity → Email Activity
- Statistics: Statistics → Overview

### Monitor

Check these regularly:
- Email Activity (delivery status)
- Statistics (bounce rates)
- Invalid Emails (remove invalid addresses)
- Spam Reports (high = bad reputation)

## Email Deliverability Tips

### Do:
- ✅ Verify your sender/domain
- ✅ Use consistent from address
- ✅ Monitor bounce rates
- ✅ Remove invalid emails
- ✅ Keep email list clean
- ✅ Use HTTPS on your site

### Don't:
- ❌ Buy email lists
- ❌ Send to inactive emails
- ❌ Use deceptive subject lines
- ❌ Send attachments
- ❌ Over-send (stay under rate limits)

## Free vs Paid

| Feature | Free | Paid |
|---------|------|------|
| Emails/day | 100 | 100,000+ |
| APIs | Limited | Full |
| Support | Community | Priority |
| Analytics | Basic | Advanced |
| Subusers | ❌ | ✅ |
| A/B Testing | ❌ | ✅ |

## Next Steps

1. ✅ SendGrid account created
2. ✅ API key generated
3. ✅ Sender verified
4. ⬜ Update .env file
5. ⬜ Test email
6. ⬜ Test password reset
7. ⬜ Monitor deliverability

## Support

- SendGrid Docs: https://docs.sendgrid.com
- Community: https://community.sendgrid.com
- Support: Available in paid plans

---

**Need Help?** 
1. Check SendGrid dashboard for errors
2. Review DNS propagation
3. Verify API key is correct
4. Contact SendGrid support if needed
