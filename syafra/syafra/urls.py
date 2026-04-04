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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect

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
    path('admin/', admin.site.urls),
    path('', include('products.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('accounts/', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
