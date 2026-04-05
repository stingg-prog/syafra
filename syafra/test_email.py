#!/usr/bin/env python
"""
Test email configuration and send a test email.
Usage:
    python test_email.py                          # Local test
    python test_email.py --production             # Simulate production check
    python test_email.py --to recipient@example.com
"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "syafra.settings")

    production_mode = "--production" in sys.argv
    test_recipient = None
    for arg in sys.argv[1:]:
        if arg.startswith("--to="):
            test_recipient = arg.split("=", 1)[1]

    import django
    django.setup()

    from django.conf import settings
    from django.core.mail import send_mail

    print("=" * 60)
    print("EMAIL CONFIGURATION TEST")
    print("=" * 60)
    print(f"DEBUG: {settings.DEBUG}")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'N/A')}")
    print(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'N/A')}")
    print(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'N/A')}")
    print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'N/A')}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"DOMAIN: {settings.DOMAIN}")
    print(f"USE_HTTPS: {settings.USE_HTTPS}")
    print("=" * 60)

    if "console" in settings.EMAIL_BACKEND:
        print("\n[WARNING] Using CONSOLE backend - emails will NOT be delivered!")
        print("   Set EMAIL_SERVICE=sendgrid or EMAIL_SERVICE=gmail in environment.\n")

    if not settings.DEBUG and "console" in settings.EMAIL_BACKEND:
        print("[ERROR] PRODUCTION: Console email backend is NOT allowed!")
        print("   Configure SendGrid or Gmail SMTP.")
        sys.exit(1)

    if test_recipient:
        print(f"\nSending test email to: {test_recipient}")
        try:
            result = send_mail(
                subject="Test Email from SYAFRA",
                message="This is a test email. If you received this, your email config is working!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[test_recipient],
                fail_silently=False,
            )
            if result:
                print(f"✅ Email sent successfully to {test_recipient}")
            else:
                print(f"❌ Email failed (returned 0)")
        except Exception as e:
            print(f"❌ Email error: {e}")
            sys.exit(1)
    else:
        print("\nTo send a test email, run: python test_email.py --to=your@email.com")
