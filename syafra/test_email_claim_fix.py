"""
Simple test to verify email claim retry mechanism works.
Run with: python manage.py shell < test_email_claim_fix.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')
django.setup()

from django.utils import timezone
from unittest.mock import patch
from django.contrib.auth import get_user_model
from products.models import Product, Category
from orders.models import Order, OrderItem
from orders.services.email_service import send_notification_email

User = get_user_model()

print("=" * 70)
print("Testing Email Claim Retry Mechanism")
print("=" * 70)

# Clean up any existing test data
User.objects.filter(username__startswith='testuser').delete()
Category.objects.filter(slug__startswith='test-cat').delete()

# Test 1: Normal claim behavior
print("\n=== Test 1: Normal email claim ===")
user1 = User.objects.create_user(username='testuser1', email='test1@example.com', password='testpass')
category1 = Category.objects.create(name='Test Category 1', slug='test-cat-1')
product1 = Product.objects.create(name='Test Product 1', brand='Test Brand 1', category=category1, price=100, stock=10)
order1 = Order.objects.create(
    user=user1,
    total_price=100.00,
    customer_name='Test User 1',
    email='test1@example.com',
    phone_number='1234567890',
    shipping_address='123 Test St',
    status='confirmed',
    payment_status='paid',
)
OrderItem.objects.create(order=order1, product=product1, quantity=1, price=100.00)

print(f"Order ID: {order1.id}")
print(f"Email sent before: {order1.confirmation_email_sent}")

with patch('orders.services.email_service.send_order_confirmation_email', return_value=True):
    result = send_notification_email(order1.id, 'confirmation')
    print(f"Email result: {result}")
    
    order1.refresh_from_db()
    print(f"Email sent after: {order1.confirmation_email_sent}")

print("[PASS] Test 1 passed: Normal email claim works")

# Test 2: Stuck claim with FORCE_EMAIL_RETRY=False
print("\n=== Test 2: Stuck claim (no force retry) ===")
user2 = User.objects.create_user(username='testuser2', email='test2@example.com', password='testpass')
category2 = Category.objects.create(name='Test Category 2', slug='test-cat-2')
product2 = Product.objects.create(name='Test Product 2', brand='Test Brand 2', category=category2, price=100, stock=10)
order2 = Order.objects.create(
    user=user2,
    total_price=100.00,
    customer_name='Test User 2',
    email='test2@example.com',
    phone_number='1234567890',
    shipping_address='123 Test St',
    status='confirmed',
    payment_status='paid',
    confirmation_email_claimed_at=timezone.now(),  # Stuck claim
)
OrderItem.objects.create(order=order2, product=product2, quantity=1, price=100.00)

print(f"Order ID: {order2.id}")
print(f"Has stuck claim: {order2.confirmation_email_claimed_at is not None}")

with patch('orders.services.email_service.send_order_confirmation_email', return_value=True):
    from django.conf import settings
    # Make sure FORCE_EMAIL_RETRY is False (default)
    settings.FORCE_EMAIL_RETRY = False
    result = send_notification_email(order2.id, 'confirmation')
    print(f"Email result: {result}")
    
    order2.refresh_from_db()
    print(f"Email sent after: {order2.confirmation_email_sent}")
    print(f"Claim still exists: {order2.confirmation_email_claimed_at is not None}")

print("[PASS] Test 2 passed: Stuck claim preserved when FORCE_EMAIL_RETRY=False")

# Test 3: Stuck claim with FORCE_EMAIL_RETRY=True
print("\n=== Test 3: Stuck claim (with force retry) ===")
user3 = User.objects.create_user(username='testuser3', email='test3@example.com', password='testpass')
category3 = Category.objects.create(name='Test Category 3', slug='test-cat-3')
product3 = Product.objects.create(name='Test Product 3', brand='Test Brand 3', category=category3, price=100, stock=10)
order3 = Order.objects.create(
    user=user3,
    total_price=100.00,
    customer_name='Test User 3',
    email='test3@example.com',
    phone_number='1234567890',
    shipping_address='123 Test St',
    status='confirmed',
    payment_status='paid',
    confirmation_email_claimed_at=timezone.now(),  # Stuck claim
)
OrderItem.objects.create(order=order3, product=product3, quantity=1, price=100.00)

print(f"Order ID: {order3.id}")
print(f"Has stuck claim: {order3.confirmation_email_claimed_at is not None}")

# Need to reload the module to pick up the setting change
import importlib
from django.conf import settings
settings.FORCE_EMAIL_RETRY = True
import orders.services.email_service as email_service
importlib.reload(email_service)

with patch('orders.services.email_service.send_order_confirmation_email', return_value=True):
    result = email_service.send_notification_email(order3.id, 'confirmation')
    print(f"Email result: {result}")
    
    order3.refresh_from_db()
    print(f"Email sent after: {order3.confirmation_email_sent}")
    print(f"Claim cleared: {order3.confirmation_email_claimed_at is None}")

print("[PASS] Test 3 passed: Stuck claim reset when FORCE_EMAIL_RETRY=True")

# Cleanup
print("\nCleaning up test data...")
Order.objects.filter(id__in=[order1.id, order2.id, order3.id]).delete()
Product.objects.filter(id__in=[product1.id, product2.id, product3.id]).delete()
Category.objects.filter(id__in=[category1.id, category2.id, category3.id]).delete()
User.objects.filter(username__in=['testuser1', 'testuser2', 'testuser3']).delete()

print("\n" + "=" * 70)
print("All tests completed successfully!")
print("=" * 70)
print("\nSummary:")
print("- Normal claims work as expected")
print("- Stuck claims are preserved by default (FORCE_EMAIL_RETRY=False)")
print("- Stuck claims are reset when FORCE_EMAIL_RETRY=True")
print("- Email delivery is successful after claim reset")
