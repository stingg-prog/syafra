from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from .password_reset_views import CustomPasswordResetView, NoCachePasswordResetConfirmView, NoCachePasswordResetCompleteView

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),

    # Password Reset - Using custom views with no-cache headers
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', NoCachePasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete'),
    ), name='password_reset_confirm'),
    
    path('reset/done/', NoCachePasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
]
