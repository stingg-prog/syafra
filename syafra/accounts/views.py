import logging

from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib import messages
from django.core.exceptions import MultipleObjectsReturned
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect, resolve_url
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags
from django.utils.http import (
    urlsafe_base64_encode,
    urlsafe_base64_decode,
    url_has_allowed_host_and_scheme,
)
from django.views.decorators.http import require_http_methods
from django.conf import settings

from orders.models import Order, PaymentSettings
from accounts.utils.email import send_email

from .forms import RegisterForm
from accounts.models import UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)


def _default_auth_backend():
    backends = getattr(settings, 'AUTHENTICATION_BACKENDS', None) or [
        'django.contrib.auth.backends.ModelBackend'
    ]
    return backends[0]


def _allowed_redirect_hosts(request):
    hosts = {request.get_host()}
    hosts.update(
        host for host in getattr(settings, 'ALLOWED_HOSTS', [])
        if host and not host.startswith('.')
    )
    domain = getattr(settings, 'DOMAIN', '').strip()
    if domain:
        hosts.add(domain)
    return hosts


def _get_safe_redirect_url(request, next_url, fallback):
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts=_allowed_redirect_hosts(request),
        require_https=request.is_secure(),
    ):
        return next_url
    return resolve_url(fallback)

def _send_password_reset_on_commit(user, request):
    sent = send_password_reset_email(user, request=request)
    return sent


def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]

            with transaction.atomic():
                user = User.objects.get(email=email)
                transaction.on_commit(lambda u=user, r=request: _send_password_reset_on_commit(u, r))

            messages.success(request, "Password reset email sent.")
            return redirect("accounts:login")

    else:
        form = PasswordResetForm()

    return render(request, "accounts/password_reset.html", {"form": form})


from django.contrib.auth.forms import SetPasswordForm
from django.utils.http import urlsafe_base64_decode


def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and default_token_generator.check_token(user, token):

        if request.method == "POST":
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Password updated successfully.")
                return redirect("accounts:login")

        else:
            form = SetPasswordForm(user)

        return render(request, "accounts/password_reset_confirm.html", {"form": form})

    return render(request, "accounts/password_reset_invalid.html")


def _find_user_by_identifier(identifier):
    username_field = getattr(User, 'USERNAME_FIELD', 'username')

    try:
        return User._default_manager.get(**{f'{username_field}__iexact': identifier})
    except User.DoesNotExist:
        if '@' not in identifier:
            return None
    except MultipleObjectsReturned:
        logger.warning('Multiple accounts found for username identifier.')
        return None

    try:
        return User._default_manager.get(email__iexact=identifier)
    except User.DoesNotExist:
        return None
    except MultipleObjectsReturned:
        logger.warning('Multiple accounts found for email identifier.')
        return None


def _authenticate_by_identifier(request, identifier, password):
    user = authenticate(request, username=identifier, password=password)
    if user is not None:
        return user

    candidate = _find_user_by_identifier(identifier)
    if candidate is None:
        return None

    return authenticate(request, username=candidate.get_username(), password=password)


def _send_activation_email(user, request):
    profile = user.profile
    raw_token = profile.set_verification_token()
    profile.save(update_fields=['email_verification_token_hash', 'email_verification_sent_at'])

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    activation_link = request.build_absolute_uri(
        reverse('accounts:activate', kwargs={'uidb64': uid, 'token': raw_token})
    )
    subject = 'Verify your email — SYAFRA'
    context = {
        'user': user,
        'activation_link': activation_link,
        'uid': uid,
        'token': raw_token,
        'domain': request.get_host(),
        'protocol': 'https' if request.is_secure() else 'http',
    }
    html_message = render_to_string('emails/account_activation_email.html', context)
    plain_message = strip_tags(html_message)
    transaction.on_commit(
        lambda: send_email(
            subject=subject,
            message=plain_message,
            recipient_list=[user.email],
            html_message=html_message,
            email_type='account_activation',
            user=user,
            metadata={'flow': 'account_activation'},
        )
    )
    return True


@require_http_methods(['GET', 'POST', 'HEAD', 'OPTIONS'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))

    next_url = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if not form.is_valid():
            return render(request, 'register.html', {'form': form, 'next': next_url})

        try:
            with transaction.atomic():
                user = form.save()
                _send_activation_email(user, request)
        except IntegrityError:
            error_message = 'This username or email is already registered.'
            form.add_error('username', error_message)
            form.add_error('email', error_message)
            return render(request, 'register.html', {'form': form, 'next': next_url})

        messages.success(
            request,
            'We\'ve sent a verification email to your email address. '
            'Please verify your email before logging in.'
        )
        return redirect('accounts:verification_sent')

    return render(request, 'register.html', {'form': RegisterForm(), 'next': next_url})


@require_http_methods(['GET', 'POST', 'HEAD', 'OPTIONS'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))

    next_url = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        username = (request.POST.get('username') or request.POST.get('email') or '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, 'Please fill in all fields.')
            return render(request, 'login.html', {'next': next_url})

        user = _authenticate_by_identifier(request, username, password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_username()}!')
            return redirect(_get_safe_redirect_url(request, next_url, settings.LOGIN_REDIRECT_URL))

        candidate = _find_user_by_identifier(username)
        if candidate is not None and candidate.check_password(password):
            if not candidate.is_active:
                profile = candidate.profile
                if not profile.email_verified:
                    uid = urlsafe_base64_encode(force_bytes(candidate.pk))
                    resend_url = reverse('accounts:resend_verification', kwargs={'uidb64': uid})
                    return render(request, 'login.html', {
                        'next': next_url,
                        'email_unverified': True,
                        'resend_url': resend_url,
                    })
                messages.error(request, 'Your account has been deactivated. Contact support.')
                return render(request, 'login.html', {'next': next_url})

        messages.error(request, 'Invalid username/email or password.')
        return render(request, 'login.html', {'next': next_url})

    return render(request, 'login.html', {'next': next_url})


@require_http_methods(['POST', 'HEAD', 'OPTIONS'])
def logout_view(request):
    """
    POST-only logout: avoids malicious <img src="/logout/"> style CSRF logout.
    Session is flushed first; flash message is stored on the new session Django opens.
    """
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect(resolve_url(settings.LOGOUT_REDIRECT_URL))


@login_required
def profile_view(request):
    # Prefetch items + product so templates iterating order lines avoid N+1 queries.
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related('items__product')
        .order_by('-created_at')[:10]
    )
    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'
    return render(request, 'profile.html', {
        'user': request.user,
        'orders': orders,
        'currency': currency,
    })


def verification_sent(request):
    return render(request, 'accounts/verification_sent.html')


@require_http_methods(['GET', 'POST', 'HEAD', 'OPTIONS'])
def resend_verification(request, uidb64=None):
    uid = None
    email = ''

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            try:
                user = User.objects.get(email__iexact=email)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
            except User.DoesNotExist:
                messages.error(request, 'No account found with that email address.')
                return render(request, 'accounts/resend_verification.html')
        else:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'accounts/resend_verification.html')

    if uidb64:
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            messages.error(request, 'Invalid verification request.')
            return redirect('accounts:login')

    if not uid:
        return render(request, 'accounts/resend_verification.html')

    if user.is_active and user.profile.email_verified:
        messages.info(request, 'Your email is already verified. Please sign in.')
        return redirect('accounts:login')

    _send_activation_email(user, request)
    messages.success(
        request,
        'A new verification email has been sent. Please check your inbox.'
    )
    return redirect('accounts:verification_sent')


def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None:
        profile = user.profile
        token_valid = profile.check_verification_token(token)
        token_expired = profile.is_token_expired()

        if token_valid and not token_expired:
            profile.verify_email()
            messages.success(request, 'Email verified successfully! You can now sign in.')
            return redirect('accounts:login')

        if token_expired:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            messages.error(request, 'Verification link has expired. A new one has been sent.')
            return redirect('accounts:resend_verification', uidb64=uid)

    messages.error(request, 'Verification link is invalid.')
    uid = urlsafe_base64_encode(force_bytes(user.pk)) if user else ''
    if uid:
        return redirect('accounts:resend_verification', uidb64=uid)
    return redirect('accounts:register')
