from django.urls import path
from . import views
from .views import razorpay_webhook_health

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('razorpay/webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    path('webhook-health/', razorpay_webhook_health, name='webhook_health'),
    path('webhook-test/', views.razorpay_webhook_test, name='razorpay_webhook_test'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('payment/verify/', views.verify_payment, name='verify_payment_legacy'),
    path('payment-success/', views.verify_payment, name='payment_success'),
    path('payment/success/', views.verify_payment, name='payment_success_legacy'),
    path('payment-failure/', views.payment_failure_callback, name='payment_failure_callback'),
    path('payment/failure/', views.payment_failure_callback, name='payment_failure_callback_legacy'),
    path('order-status/<int:order_id>/', views.order_status, name='order_status'),
    path('order-failed/', views.payment_failed, name='payment_failed'),
    path('payment/failed/', views.payment_failed, name='payment_failed_legacy'),
    path('retry/<int:order_id>/', views.retry_payment, name='retry_payment'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('success/<int:order_id>/', views.order_success, name='order_success_legacy'),
    path('history/', views.order_history, name='order_history'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('upi/verify/', views.upi_payment_verify, name='upi_payment_verify'),
]
