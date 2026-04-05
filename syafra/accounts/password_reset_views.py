"""
Custom Password Reset Views with improved email handling
"""
import logging

from django.contrib.auth.views import PasswordResetView as BasePasswordResetView
from django.contrib.auth.views import PasswordResetDoneView as BasePasswordResetDoneView
from django.contrib.auth.views import PasswordResetCompleteView as BasePasswordResetCompleteView
from django.contrib.auth.views import PasswordResetConfirmView as BasePasswordResetConfirmView
from django.urls import reverse_lazy
from django.conf import settings
from django.http import HttpResponse
from .forms import PasswordResetForm

logger = logging.getLogger(__name__)


class CustomPasswordResetView(BasePasswordResetView):
    """
    Custom password reset view with improved email handling.
    
    Features:
    - Fresh token generation per request (handled by Django)
    - Instant email delivery via SendGrid SMTP
    - No caching of reset links
    - Comprehensive logging
    """
    form_class = PasswordResetForm
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.txt'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    html_email_template_name = 'registration/password_reset_email.html'
    fail_silently = False
    
    def get_from_email(self):
        return settings.DEFAULT_FROM_EMAIL
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['domain'] = settings.DOMAIN
        context['protocol'] = 'https' if settings.USE_HTTPS else 'http'
        return context
    
    def get_extra_email_context(self):
        return {
            'domain': settings.DOMAIN,
            'protocol': 'https' if settings.USE_HTTPS else 'http',
        }
    
    def send_mail(self, *args, **kwargs):
        subject = args[0] if args else kwargs.get('subject', 'Password Reset')
        to_email = args[1] if len(args) > 1 else kwargs.get('to_email', 'Unknown')
        logger.info(f"PASSWORD RESET EMAIL SENT INSTANTLY | to={to_email} | subject={subject}")
        try:
            super().send_mail(*args, **kwargs)
            logger.info(f"PASSWORD RESET EMAIL DELIVERED | to={to_email}")
        except Exception as e:
            logger.error(f"PASSWORD RESET EMAIL FAILED | to={to_email} | error={e}")
            raise


class NoCachePasswordResetConfirmView(BasePasswordResetConfirmView):
    """
    Password reset confirm view with no-cache headers.
    Ensures fresh token validation each time.
    """
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')
    post_reset_login = False
    post_reset_login_backend = None
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


class NoCachePasswordResetCompleteView(BasePasswordResetCompleteView):
    """
    Password reset complete view with no-cache headers.
    """
    template_name = 'registration/password_reset_complete.html'
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


# Export the views
PasswordResetView = CustomPasswordResetView
PasswordResetDoneView = BasePasswordResetDoneView
PasswordResetConfirmView = NoCachePasswordResetConfirmView
PasswordResetCompleteView = NoCachePasswordResetCompleteView
