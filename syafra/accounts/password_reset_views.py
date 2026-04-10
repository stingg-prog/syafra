"""
Custom Password Reset Views with improved email handling
"""
import logging

from django.contrib.auth.views import PasswordResetView as BasePasswordResetView
from django.contrib.auth.views import PasswordResetDoneView as BasePasswordResetDoneView
from django.contrib.auth.views import PasswordResetCompleteView as BasePasswordResetCompleteView
from django.contrib.auth.views import PasswordResetConfirmView as BasePasswordResetConfirmView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.conf import settings
from .forms import PasswordResetForm

logger = logging.getLogger(__name__)


class CustomPasswordResetView(BasePasswordResetView):
    """
    Custom password reset view with improved email handling.
    
    Features:
    - Fresh token generation per request (handled by Django)
    - Instant email delivery via the direct SendGrid API
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

    def form_valid(self, form):
        recipient = form.cleaned_data.get('email', '')
        logger.info("PASSWORD RESET REQUEST RECEIVED | to=%s", recipient)
        form.save(
            use_https=settings.USE_HTTPS,
            token_generator=self.token_generator,
            from_email=settings.DEFAULT_FROM_EMAIL,
            email_template_name=self.email_template_name,
            subject_template_name=self.subject_template_name,
            request=self.request,
            html_email_template_name=self.html_email_template_name,
            extra_email_context={
                'domain': settings.DOMAIN,
                'protocol': 'https' if settings.USE_HTTPS else 'http',
            },
            domain_override=settings.DOMAIN,
        )
        logger.info("PASSWORD RESET EMAIL QUEUED | to=%s", recipient)
        return HttpResponseRedirect(self.get_success_url())


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
