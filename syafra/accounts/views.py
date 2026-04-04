from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str

from .utils.email import send_email
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
    send_email(subject, plain_message, [user.email], html_message=html_message)


@require_http_methods(['GET', 'POST', 'HEAD', 'OPTIONS'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')

    next_url = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if not form.is_valid():
            return render(request, 'register.html', {'form': form, 'next': next_url})

        try:
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                is_active=False,
            )
        except IntegrityError as exc:
            error_message = 'This username or email is already registered.'
            form.add_error('username', error_message)
            form.add_error('email', error_message)
            return render(request, 'register.html', {'form': form, 'next': next_url})

        try:
            _send_activation_email(user, request)
            messages.success(request, 'Registration successful! Check your email to activate your account.')
        except Exception:
            messages.warning(request, 'Account created, but activation email could not be sent. Contact support.')

        redirect_url = 'accounts:login'
        return redirect(redirect_url)

    return render(request, 'register.html', {'form': RegisterForm(), 'next': next_url})


@require_http_methods(['GET', 'POST', 'HEAD', 'OPTIONS'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')

    next_url = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password:
            messages.error(request, 'Please fill in all fields.')
            return render(request, 'login.html', {'next': next_url})

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, 'Account not activated. Please check your email.')
                return render(request, 'login.html', {'next': next_url})

            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')

            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect('products:home')

        messages.error(request, 'Invalid username or password.')
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
    return redirect('products:home')


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
