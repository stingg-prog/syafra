from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import PasswordResetForm as BasePasswordResetForm
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.conf import settings
import logging

from accounts.utils.email import send_email as send_syafra_email

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
        username = self.cleaned_data['username'].strip()
        username_field = getattr(User, 'USERNAME_FIELD', 'username')
        if User.objects.filter(**{f'{username_field}__iexact': username}).exists():
            raise ValidationError('Username already exists.')
        return username

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data['email'].strip())
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

    def save(self):
        username_field = getattr(User, 'USERNAME_FIELD', 'username')
        user = User(
            **{
                username_field: self.cleaned_data['username'],
                'email': self.cleaned_data['email'],
                'is_active': True,
            }
        )
        user.set_password(self.cleaned_data['password'])
        user.save()
        return user


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
            email_context = dict(context)
            
            # Send HTML email if template exists
            if html_email_template_name:
                html_message = render_to_string(html_email_template_name, email_context)
                plain_message = render_to_string(email_template_name, email_context)
                sent = send_syafra_email(
                    subject=subject,
                    message=plain_message,
                    recipient_list=[to_email],
                    html_message=html_message,
                    from_email=from_email,
                    email_type="password_reset",
                    user=context.get("user"),
                    metadata={"flow": "password_reset_form"},
                )
                if not sent:
                    raise ValueError("Password reset HTML email failed to send")
                logger.info(f"Password reset HTML email sent to: {to_email}")
            else:
                # Plain text only
                message = render_to_string(email_template_name, email_context)
                sent = send_syafra_email(
                    subject=subject,
                    message=message,
                    recipient_list=[to_email],
                    from_email=from_email,
                    email_type="password_reset",
                    user=context.get("user"),
                    metadata={"flow": "password_reset_form"},
                )
                if not sent:
                    raise ValueError("Password reset plain text email failed to send")
                logger.info(f"Password reset plain text email sent to: {to_email}")
                
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
            raise  # Re-raise to show error to user
