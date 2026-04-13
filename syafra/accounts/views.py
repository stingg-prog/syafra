import logging

from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.exceptions import MultipleObjectsReturned
from django.db import IntegrityError
from django.shortcuts import render, redirect, resolve_url
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode

from .forms import PasswordResetForm
from accounts.utils.email import send_email
from django.utils.html import strip_tags
from django.utils.http import (
    urlsafe_base64_encode,
    urlsafe_base64_decode,
    url_has_allowed_host_and_scheme,
)
from django.views.decorators.http import require_http_methods
from django.conf import settings

from orders.models import Order, PaymentSettings

from .forms import RegisterForm

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

def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.get(email=email)

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_link = f"https://yourdomain.com/reset/{uid}/{token}/"

            subject = "Password Reset Request"
            message = f"""
            Click the link below to reset your password:

            {reset_link}
            """

            # 🔥 INSTANT EMAIL (NO DELAY)
            send_email(
                subject=subject,
                message=message,
                recipient_list=[email],
            )

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
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_link = request.build_absolute_uri(
        reverse('accounts:activate', kwargs={'uidb64': uid, 'token': token})
    )
    subject = 'Activate your SYAFRA account'
    context = {
        'user': user,
        'activation_link': activation_link,
        'uid': uid,
        'token': token,
        'domain': request.get_host(),
        'protocol': 'https' if request.is_secure() else 'http',
    }
    html_message = render_to_string('emails/account_activation_email.html', context)
    plain_message = strip_tags(html_message)
    return send_email(
        subject=subject,
        message=plain_message,
        recipient_list=[user.email],
        html_message=html_message,
        email_type='account_activation',
        user=user,
        metadata={'flow': 'account_activation'},
    )


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
            user = form.save()
        except IntegrityError:
            error_message = 'This username or email is already registered.'
            form.add_error('username', error_message)
            form.add_error('email', error_message)
            return render(request, 'register.html', {'form': form, 'next': next_url})

        login(request, user, backend=_default_auth_backend())
        messages.success(request, 'Your account has been created and you are now signed in.')
        return redirect(_get_safe_redirect_url(request, next_url, settings.LOGIN_REDIRECT_URL))

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
        if (
            candidate is not None
            and not candidate.is_active
            and candidate.last_login is None
            and candidate.check_password(password)
        ):
            candidate.is_active = True
            candidate.save(update_fields=['is_active'])
            login(request, candidate, backend=_default_auth_backend())
            messages.success(request, 'Your account has been activated and you are now signed in.')
            return redirect(_get_safe_redirect_url(request, next_url, settings.LOGIN_REDIRECT_URL))

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


def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        messages.success(request, 'Your account has been activated. Please sign in.')
        return redirect('accounts:login')

    messages.error(request, 'Activation link is invalid or has expired.')
    return redirect('accounts:register')
