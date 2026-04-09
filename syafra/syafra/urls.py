from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect
from django.views.generic.base import RedirectView

from orders import views as order_views

handler404 = 'syafra.views.custom_page_not_found'
handler500 = 'syafra.views.custom_server_error'


def favicon_redirect(request):
    return redirect(staticfiles_storage.url("images/syafra_logo.png"), permanent=True)


def custom_method_not_allowed(request, exception=None):
    """Handle HTTP 405 Method Not Allowed errors gracefully."""
    if request.path.startswith('/orders/payment/') or request.path.startswith('/orders/upi/'):
        return redirect('cart:cart_view')
    return HttpResponseNotAllowed(
        content=b'<html><body><h1>Method Not Allowed</h1><p>The page you requested does not support this HTTP method.</p><a href="/">Go Home</a></body></html>',
        content_type='text/html'
    )

handler405 = custom_method_not_allowed

urlpatterns = [
    path('favicon.ico', favicon_redirect),
    path('admin/analytics/', order_views.analytics_dashboard, name='analytics_dashboard'),
    path('admin/', admin.site.urls),
    path('password_reset/', RedirectView.as_view(pattern_name='accounts:password_reset', permanent=False)),
    path('password_reset_done/', RedirectView.as_view(pattern_name='accounts:password_reset_done', permanent=False)),
    path('reset/<uidb64>/<token>/', RedirectView.as_view(pattern_name='accounts:password_reset_confirm', permanent=False)),
    path('reset_done/', RedirectView.as_view(pattern_name='accounts:password_reset_complete', permanent=False)),
    path('', include('products.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('accounts/', include('accounts.urls')),
]
