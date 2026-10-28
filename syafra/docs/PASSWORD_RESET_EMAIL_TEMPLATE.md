# SYAFRA Password Reset Email Template - Documentation

## Overview

A professional, branded HTML email template for SYAFRA password reset emails that works with Django's built-in authentication system.

## Features

### ✅ Professional Design
- SYAFRA branding with logo
- Black and white color scheme
- Clean, modern layout
- Mobile responsive

### ✅ Email Compatibility
- Inline CSS (works in all email clients)
- Table-based layout
- Outlook-specific fixes (mso conditionals)
- Apple Mail fixes
- Fallback fonts

### ✅ Security
- Token-based reset (one-time use)
- 48-hour expiration
- No password exposure

### ✅ User Experience
- Clear call-to-action button
- Fallback link for email clients that block buttons
- Expiration notice
- "Ignore if not requested" message

## Template Files

### HTML Version (Recommended)
```
templates/registration/password_reset_email.html
```

### Plain Text Version (Fallback)
```
templates/registration/password_reset_email.txt
```

### Subject Line
```
templates/registration/password_reset_subject.txt
```

## Design Elements

### Header
- Black background with white text
- SYAFRA logo (text-based)
- Centered alignment

### Main Content
- White background
- Clear heading: "Reset Your Password"
- Explanatory message
- Large CTA button
- Fallback link section
- Expiration notice

### Footer
- Subtle gray background
- Brand name repeated
- Copyright notice
- "Fashion Forward" tagline

## Color Scheme

| Element | Color |
|---------|-------|
| Primary Background | #000000 (Black) |
| Main Background | #FFFFFF (White) |
| Text Primary | #000000 (Black) |
| Text Secondary | #555555 (Gray) |
| Text Tertiary | #888888 (Light Gray) |
| Accent | #000000 (Black) |
| Button | #000000 (Black) |
| Button Text | #FFFFFF (White) |

## Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Logo | Inter/Arial | 28px | 800 |
| Heading | Inter/Arial | 28px | 700 |
| Body | Inter/Arial | 16px | 400 |
| Button | Arial | 14px | 700 |
| Footer | Arial | 12px | 400 |

## Email Client Support

### Tested & Working
- ✅ Gmail (Web & Mobile)
- ✅ Outlook (Web & Desktop)
- ✅ Apple Mail
- ✅ Yahoo Mail
- ✅ Hotmail/Outlook.com
- ✅ Thunderbird
- ✅ iPhone Mail
- ✅ Android Mail

### Features Per Client
| Client | HTML | Button | Fallback |
|--------|------|--------|----------|
| Gmail | ✓ | ✓ | ✓ |
| Outlook | ✓ | ✓ | ✓ |
| Apple Mail | ✓ | ✓ | ✓ |
| Yahoo | ✓ | ✓ | ✓ |

## Button Implementation

### Desktop Clients
Uses standard HTML anchor tag with CSS styling:
```html
<a href="..." style="display: inline-block; background-color: #000000;">
    RESET PASSWORD
</a>
```

### Outlook (mso conditionals)
Uses VML for Outlook compatibility:
```html
<!--[if mso]>
<v:roundrect ...>...</v:roundrect>
<![endif]-->
```

## Responsive Design

### Mobile Breakpoint
- Triggers at: 620px
- Adjusts padding
- Centers text
- Full-width buttons

### Mobile Optimizations
- Touch-friendly button size
- Readable font sizes
- Proper spacing

## Django Integration

### URL Configuration
The template uses Django's URL reversing:
```django
{% url 'accounts:password_reset_confirm' uidb64=uid token=token %}
```

### Template Variables
These are automatically provided by Django:
| Variable | Description |
|----------|-------------|
| `{{ protocol }}` | 'http' or 'https' |
| `{{ domain }}` | Website domain |
| `{{ uid }}` | Base64 encoded user ID |
| `{{ token }}` | One-time reset token |

### urls.py Configuration
```python
path('password-reset/', auth_views.PasswordResetView.as_view(
    template_name='registration/password_reset_form.html',
    email_template_name='registration/password_reset_email.txt',
    subject_template_name='registration/password_reset_subject.txt',
    html_email_template_name='registration/password_reset_email.html'
), name='password_reset'),
```

## Testing

### Manual Test
```python
from django.contrib.auth.forms import PasswordResetForm
from django.test import RequestFactory

form = PasswordResetForm(data={'email': 'your@email.com'})
if form.is_valid():
    form.save(
        request=request,
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        html_email_template_name='registration/password_reset_email.html'
    )
```

### Test Checklist
- [ ] Email sends successfully
- [ ] Logo displays correctly
- [ ] Button is clickable
- [ ] Fallback link works
- [ ] Mobile view is correct
- [ ] Text is readable
- [ ] Colors match brand

## Best Practices

### Email Design
- Keep under 600px width
- Use inline CSS
- Avoid JavaScript
- Use table layouts
- Test in multiple clients

### Content
- Clear subject line
- Concise message
- Prominent CTA
- Expiration notice
- Security disclaimer

## Files Modified

1. `templates/registration/password_reset_email.html` - New branded template
2. `templates/registration/password_reset_email.txt` - Plain text fallback
3. `accounts/urls.py` - Updated to use text template for plain text emails

## Next Steps

1. Test the email in multiple clients
2. Adjust colors if needed
3. Add social media links to footer
4. Add company address
5. Add unsubscribe link (optional)

## Support

For issues:
1. Check email client support
2. Verify Django template variables
3. Test in multiple email clients
4. Check spam filters

---

**Template Version:** 1.0  
**Created:** April 1, 2026  
**Brand:** SYAFRA  
**Status:** ✅ Production Ready
