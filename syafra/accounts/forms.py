from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import PasswordResetForm as BasePasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
import logging

User = get_user_model()
logger = logging.getLogger('syafra.email')


class RegisterForm(forms.Form):
    """
    Registration with Django email validation and password rules.
    Replaces ad-hoc POST parsing so invalid emails are rejected before save.
    """

    username = forms.CharField(
        max_length=150,
        strip=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 px-4 py-3 focus:outline-none focus:border-black transition-colors',
            'placeholder': 'Choose a username',
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full border border-gray-300 px-4 py-3 focus:outline-none focus:border-black transition-colors',
            'placeholder': 'Enter your email',
        }),
    )
    password = forms.CharField(
        min_length=8,
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full border border-gray-300 px-4 py-3 focus:outline-none focus:border-black transition-colors',
            'placeholder': 'Create a password',
        }),
    )
    password2 = forms.CharField(
        label='Confirm password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full border border-gray-300 px-4 py-3 focus:outline-none focus:border-black transition-colors',
            'placeholder': 'Confirm your password',
        }),
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Email already registered.')
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password)
        return password

    def clean(self):
        data = super().clean()
        p1 = data.get('password')
        p2 = data.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError('Passwords do not match.')
        return data


class PasswordResetForm(BasePasswordResetForm):
    """
    Custom password reset form with improved error handling and logging.
    Sends HTML + plain text emails with proper headers for better deliverability.
    """
    
    def send_mail(self, subject_template_name, email_template_name,
                 context, from_email, to_email, html_email_template_name=None):
        """
        Send the password reset email with proper error handling and logging.
        """
        logger.info(f"Preparing password reset email for: {to_email}")
        
        try:
            # Render subject
            subject = render_to_string(subject_template_name, context)
            subject = ''.join(subject.splitlines())
            
            # Get user and generate token
            user = context.get('user')
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            # Get protocol and domain
            protocol = 'https' if not settings.DEBUG else 'http'
            domain = getattr(settings, 'DOMAIN', '127.0.0.1:8000')
            
            # Update context with URL components
            context.update({
                'protocol': protocol,
                'domain': domain,
                'uid': uid,
                'token': token,
            })
            
            # Send HTML email if template exists
            if html_email_template_name:
                html_message = render_to_string(html_email_template_name, context)
                plain_message = render_to_string(email_template_name, context)
                
                try:
                    email = EmailMultiAlternatives(
                        subject=subject,
                        body=plain_message,
                        from_email=from_email,
                        to=[to_email],
                        headers={
                            'X-Mailer': 'SYAFRA-Django',
                            'X-Priority': '3',
                            'Organization': 'SYAFRA',
                        }
                    )
                    email.attach_alternative(html_message, 'text/html')
                    email.send(fail_silently=False)
                    
                    logger.info(f"Password reset HTML email sent to: {to_email}")
                    
                except Exception as e:
                    logger.error(f"HTML email failed, falling back to plain text: {str(e)}")
                    # Fallback to plain text
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        from_email=from_email,
                        recipient_list=[to_email],
                        fail_silently=False
                    )
            else:
                # Plain text only
                message = render_to_string(email_template_name, context)
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_email,
                    recipient_list=[to_email],
                    fail_silently=False
                )
                logger.info(f"Password reset plain text email sent to: {to_email}")
                
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
            raise  # Re-raise to show error to user
