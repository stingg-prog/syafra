from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render

_MAINTENANCE_CACHE_KEY = 'maintenance_mode_status'
_MAINTENANCE_CACHE_TTL = 60


class MaintenanceModeMiddleware:
    EXEMPT_PATHS = (
        '/admin/',
        '/accounts/login/',
        '/accounts/logout/',
        '/static/',
        '/media/',
        '/orders/razorpay/webhook/',
        '/orders/webhook-health/',
        '/orders/webhook-test/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        settings_data = cache.get(_MAINTENANCE_CACHE_KEY)
        if settings_data is None:
            from .models import WebsiteSettings
            ws = WebsiteSettings.get_settings()
            settings_data = {
                'maintenance_mode': ws.maintenance_mode,
                'maintenance_message': ws.maintenance_message,
            }
            cache.set(_MAINTENANCE_CACHE_KEY, settings_data, _MAINTENANCE_CACHE_TTL)

        if settings_data['maintenance_mode']:
            if request.user.is_staff or request.user.is_superuser:
                return self.get_response(request)

            path = request.path.lower()
            for exempt in self.EXEMPT_PATHS:
                if path.startswith(exempt):
                    return self.get_response(request)

            return render(request, 'maintenance.html', {
                'message': settings_data['maintenance_message'],
            }, status=503)

        return self.get_response(request)
