from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


def send_email(subject, message, recipient_list, html_message=None, from_email=None):
    """
    Send an email with optional HTML content.

    This helper centralizes Django email sending so the project can
    reuse consistent subject, sender, and HTML support.
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    logger.info(f"EMAIL SENT INSTANTLY | subject={subject} | to={recipient_list} | backend={settings.EMAIL_BACKEND}")

    try:
        if html_message:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list
            )
            msg.attach_alternative(html_message, 'text/html')
            msg.send(fail_silently=False)
        else:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
        logger.info(f"EMAIL SENT SUCCESS | subject={subject} | to={recipient_list}")
        return True
    except Exception as e:
        logger.error(f"EMAIL FAILED | subject={subject} | to={recipient_list}: {str(e)}")
        raise


def send_password_reset_email(user, request=None):
    """
    Send password reset email to user.
    
    Args:
        user: User model instance
        request: HTTP request (optional, for getting domain)
    
    Returns:
        bool: True if email was sent successfully
    """
    from django.urls import reverse
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.contrib.auth.tokens import default_token_generator
    
    try:
        if request:
            protocol = 'https' if request.is_secure() else 'http'
            domain = request.get_host()
        else:
            protocol = 'https' if settings.USE_HTTPS else 'http'
            allowed_hosts = settings.ALLOWED_HOSTS
            if isinstance(allowed_hosts, list) and allowed_hosts:
                domain = allowed_hosts[0]
            elif isinstance(allowed_hosts, str):
                domain = allowed_hosts.split(',')[0]
            else:
                domain = 'localhost'
        
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        reset_url = f"{protocol}://{domain}{reverse('accounts:password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})}"
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'protocol': protocol,
            'domain': domain,
            'uidb64': uidb64,
            'token': token,
        }
        
        subject = render_to_string('registration/password_reset_subject.txt').strip()
        html_message = render_to_string('registration/password_reset_email.html', context)
        plain_message = f"""
Hello {user.username or user.email},

You have requested a password reset for your SYAFRA account.

Click the link below to reset your password:
{reset_url}

If you did not request this, you can ignore this email.

Thanks,
SYAFRA Team
        """.strip()
        
        send_email(
            subject=subject,
            message=plain_message,
            recipient_list=[user.email],
            html_message=html_message
        )
        
        logger.info(f"Password reset email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False


def test_email_configuration():
    """
    Test email configuration and return diagnostic information.
    
    Returns:
        dict: Diagnostic information about email configuration
    """
    import socket
    
    diagnostics = {
        'backend': settings.EMAIL_BACKEND,
        'host': getattr(settings, 'EMAIL_HOST', 'Not configured'),
        'port': getattr(settings, 'EMAIL_PORT', 'Not configured'),
        'use_tls': getattr(settings, 'EMAIL_USE_TLS', 'Not configured'),
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'debug_mode': settings.DEBUG,
    }
    
    if 'console' in settings.EMAIL_BACKEND:
        diagnostics['warning'] = 'Using console backend - emails print to terminal, not sent to inbox'
    elif 'smtp' in settings.EMAIL_BACKEND:
        diagnostics['warning'] = 'Using SMTP backend - emails will be sent to real inbox'
        
        try:
            socket.create_connection((settings.EMAIL_HOST, settings.EMAIL_PORT), timeout=5)
            diagnostics['smtp_connection'] = 'Success'
        except Exception as e:
            diagnostics['smtp_connection'] = f'Failed: {str(e)}'
    
    return diagnostics


def send_test_email(recipient):
    """
    Send a test email to verify configuration.
    
    Args:
        recipient: Email address to send test to
        
    Returns:
        bool: True if email was sent successfully
    """
    return send_email(
        subject='Test Email from SYAFRA',
        message='This is a test email to verify email configuration is working.',
        recipient_list=[recipient],
        html_message='<h1>Test Email</h1><p>This is a test email from SYAFRA.</p>'
    )
