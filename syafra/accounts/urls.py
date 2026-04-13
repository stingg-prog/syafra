from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import sendgrid_webhooks

from .views import password_reset_request, password_reset_confirm


app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),

    # Password Reset - Using custom views with no-cache headers
    path("password-reset/", password_reset_request, name="password_reset"),
    
    
    path("reset/<uidb64>/<token>/", password_reset_confirm, name="password_reset_confirm"),

]
