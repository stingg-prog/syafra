"""
URL configuration for syafra project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
    Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
    Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
    Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os

from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect
from django.views.static import serve
from django.views.generic.base import RedirectView
from orders import views as order_views

handler404 = 'syafra.views.custom_page_not_found'
handler500 = 'syafra.views.custom_server_error'

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

if os.getenv("SERVE_MEDIA_VIA_DJANGO") == "true":
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]
