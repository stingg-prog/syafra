from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


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
        from .models import WebsiteSettings
        website_settings = WebsiteSettings.get_settings()

        if website_settings.maintenance_mode:
            if request.user.is_staff or request.user.is_superuser:
                return self.get_response(request)

            path = request.path.lower()
            for exempt in self.EXEMPT_PATHS:
                if path.startswith(exempt):
                    return self.get_response(request)

            return render(request, 'maintenance.html', {
                'message': website_settings.maintenance_message,
            }, status=503)

        return self.get_response(request)
