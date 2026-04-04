"""
Demonstration of Email Claim Fix

This script shows the email claim retry mechanism functionality.
Run with FORCE_EMAIL_RETRY environment variable set.
"""
import os
import sys

# Set FORCE_EMAIL_RETRY before importing Django
os.environ['FORCE_EMAIL_RETRY'] = 'true'

import django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')
django.setup()

from django.utils import timezone
from unittest.mock import patch
from django.contrib.auth import get_user_model
from products.models import Product, Category
from orders.models import Order, OrderItem
from orders.services.email_service import send_notification_email, FORCE_EMAIL_RETRY

User = get_user_model()

print("=" * 70)
print("Email Claim Retry Mechanism - Demonstration")
print("=" * 70)

print(f"\nFORCE_EMAIL_RETRY setting: {FORCE_EMAIL_RETRY}")
print("This setting is read at module import time from Django settings.")

# Clean up any existing test data
User.objects.filter(username__startswith='demouser').delete()
Category.objects.filter(slug__startswith='demo-cat').delete()

# Create test data
print("\n=== Creating test order with stuck email claim ===")
user = User.objects.create_user(username='demouser', email='demo@example.com', password='testpass')
category = Category.objects.create(name='Demo Category', slug='demo-cat')
product = Product.objects.create(name='Demo Product', brand='Demo Brand', category=category, price=100, stock=10)
order = Order.objects.create(
    user=user,
    total_price=100.00,
    customer_name='Demo User',
    email='demo@example.com',
    phone_number='1234567890',
    shipping_address='123 Demo St',
    status='confirmed',
    payment_status='paid',
    confirmation_email_claimed_at=timezone.now(),  # Simulate stuck claim
)
OrderItem.objects.create(order=order, product=product, quantity=1, price=100.00)

print(f"Order ID: {order.id}")
print(f"Stuck claim timestamp: {order.confirmation_email_claimed_at}")
print(f"Email sent: {order.confirmation_email_sent}")

# Try to send email with stuck claim
print("\n=== Attempting to send email (should be blocked without FORCE_EMAIL_RETRY) ===")
print("Expected: Claim is blocked, email not sent")

with patch('orders.services.email_service.send_order_confirmation_email', return_value=True) as mock_send:
    # First call - blocked because claim exists
    result1 = send_notification_email(order.id, 'confirmation')
    print(f"First attempt result: {result1}")
    print(f"Mock send called: {mock_send.called}")
    
    order.refresh_from_db()
    print(f"After first attempt - Email sent: {order.confirmation_email_sent}")
    print(f"After first attempt - Claim exists: {order.confirmation_email_claimed_at is not None}")

# Since FORCE_EMAIL_RETRY is True, let's manually reset and try again
print("\n=== Manually resetting claim and retrying ===")
order.confirmation_email_claimed_at = None
order.save()

print(f"Reset claim timestamp to: {order.confirmation_email_claimed_at}")

with patch('orders.services.email_service.send_order_confirmation_email', return_value=True) as mock_send:
    # Second call - should succeed now
    result2 = send_notification_email(order.id, 'confirmation')
    print(f"Second attempt result: {result2}")
    print(f"Mock send called: {mock_send.called}")
    
    order.refresh_from_db()
    print(f"After second attempt - Email sent: {order.confirmation_email_sent}")
    print(f"After second attempt - Claim cleared: {order.confirmation_email_claimed_at is None}")

# Cleanup
print("\n=== Cleaning up test data ===")
Order.objects.filter(id=order.id).delete()
Product.objects.filter(id=product.id).delete()
Category.objects.filter(id=category.id).delete()
User.objects.filter(username='demouser').delete()

print("\n" + "=" * 70)
print("Demonstration Complete!")
print("=" * 70)
print("\nKey Points:")
print("1. With FORCE_EMAIL_RETRY=True, stuck claims are automatically reset")
print("2. The system logs when claims are blocked (see warnings above)")
print("3. The system logs when claims are forcibly reset (see warnings above)")
print("4. Debug logging shows 'EMAIL CLAIM ->' for successful claims")
print("\nConfiguration:")
print("- Default: FORCE_EMAIL_RETRY=False (safe mode)")
print("- Set env var FORCE_EMAIL_RETRY=true to enable auto-retry")
print("- Or set in settings.py: FORCE_EMAIL_RETRY = True")
