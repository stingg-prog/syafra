import hashlib
import hmac
import json
from datetime import timedelta

from django.core import mail
from django.contrib.admin.sites import AdminSite
from django.test import TestCase, Client, override_settings
from django.db import IntegrityError
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test.client import RequestFactory
from django.utils import timezone
from unittest import mock
from accounts.models import EmailLog
from products.models import Category, Product
from cart.models import Cart, CartItem
from .admin import OrderAdmin
from .models import Order, OrderItem, Payment, PaymentSettings

User = get_user_model()


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            brand='Test Brand',
            category=self.category,
            price=100.00,
            stock=10
        )

    def test_order_creation(self):
        order = Order.objects.create(
            user=self.user,
            total_price=200.00,
            customer_name='John Doe',
            email='john@example.com',
            phone_number='1234567890',
            shipping_address='123 Test St',
            status='pending'
        )
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.customer_name, 'John Doe')
        self.assertEqual(order.email, 'john@example.com')
        self.assertEqual(order.status, 'pending')

    def test_order_str(self):
        order = Order.objects.create(
            user=self.user,
            total_price=200.00,
            customer_name='John Doe',
            email='john@example.com',
            phone_number='1234567890',
            shipping_address='123 Test St'
        )
        self.assertIn('Order', str(order))


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='SYAFRA <noreply@syafra.com>',
)
class InstantOrderEmailSystemTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='testpass123',
        )
        self.user = User.objects.create_user(
            username='emailflowuser',
            email='customer@example.com',
            password='testpass123',
        )
        self.category = Category.objects.create(name='Email Category', slug='email-category')
        self.product = Product.objects.create(
            name='Email Product',
            brand='Email Brand',
            category=self.category,
            price=100.00,
            stock=10,
        )
        self.order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Email Flow User',
            email='customer@example.com',
            phone_number='9876543210',
            shipping_address='123 Email Flow Street',
            status='pending',
            payment_status='pending',
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

    def test_send_order_email_is_idempotent_for_same_event(self):
        from .services.email_service import send_order_email

        first_sent = send_order_email(self.order, 'shipped')
        second_sent = send_order_email(self.order, 'shipped')

        self.assertTrue(first_sent)
        self.assertFalse(second_sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            EmailLog.objects.filter(
                order=self.order,
                correlation_id=str(self.order.id),
                event_type='shipped',
            ).count(),
            1,
        )

    def test_send_order_email_does_not_retry_failed_event_log(self):
        from .services.email_service import send_order_email

        EmailLog.objects.create(
            email_type=EmailLog.TYPE_ORDER_CONFIRMATION,
            event_type='cancelled',
            user=self.user,
            order=self.order,
            recipient='customer@example.com',
            recipient_domain='example.com',
            subject='Order Created - Order #1',
            status=EmailLog.STATUS_FAILED,
            correlation_id=str(self.order.id),
            error_message='Invalid recipient email address.',
        )

        outbox_count = len(mail.outbox)

        sent = send_order_email(self.order, 'cancelled')

        self.assertFalse(sent)
        self.assertEqual(len(mail.outbox), outbox_count)
        self.assertEqual(
            EmailLog.objects.filter(
                order=self.order,
                correlation_id=str(self.order.id),
                event_type='cancelled',
            ).count(),
            1,
        )

    def test_status_change_helper_sends_event_email_immediately(self):
        from .services.email_service import send_order_status_email_if_changed

        with mock.patch('orders.services.email_service.send_order_email', return_value=True) as send_mock:
            sent = send_order_status_email_if_changed(self.order, 'pending', 'shipped')

        self.assertTrue(sent)
        send_mock.assert_called_once_with(self.order, 'shipped')

    def test_same_status_update_does_not_send_event_email(self):
        from .services.email_service import send_order_status_email_if_changed

        with mock.patch('orders.services.email_service.send_order_email', return_value=True) as send_mock:
            sent = send_order_status_email_if_changed(self.order, 'pending', 'pending')

        self.assertFalse(sent)
        send_mock.assert_not_called()

    def test_admin_save_model_sends_created_email_immediately(self):
        admin_instance = OrderAdmin(Order, AdminSite())
        request = self.factory.post('/admin/orders/order/add/')
        request.user = self.admin_user
        admin_order = Order(
            user=self.user,
            total_price=150.00,
            customer_name='Admin Created Customer',
            email='customer@example.com',
            phone_number='9876543210',
            shipping_address='456 Admin Street',
            status='pending',
            payment_status='pending',
        )

        with mock.patch('orders.admin.send_order_email', return_value=True) as send_mock:
            admin_instance.save_model(request, admin_order, form=None, change=False)

        send_mock.assert_called_once()
        sent_order, event_type = send_mock.call_args.args
        self.assertEqual(sent_order.id, admin_order.id)
        self.assertEqual(event_type, 'created')

    def test_admin_save_model_update_does_not_send_created_email(self):
        admin_instance = OrderAdmin(Order, AdminSite())
        request = self.factory.post(f'/admin/orders/order/{self.order.id}/change/')
        request.user = self.admin_user
        self.order.customer_name = 'Admin Updated Customer'

        with mock.patch('orders.admin.send_order_email', return_value=True) as send_mock, mock.patch('orders.admin.send_order_status_email_if_changed', return_value=True) as status_mock:
            admin_instance.save_model(request, self.order, form=None, change=True)

        send_mock.assert_not_called()
        status_mock.assert_not_called()

    def test_admin_save_model_status_update_sends_status_email_immediately(self):
        admin_instance = OrderAdmin(Order, AdminSite())
        request = self.factory.post(f'/admin/orders/order/{self.order.id}/change/')
        request.user = self.admin_user
        self.order.status = 'shipped'

        with mock.patch('orders.admin.send_order_status_email_if_changed', return_value=True) as status_mock:
            admin_instance.save_model(request, self.order, form=None, change=True)

        status_mock.assert_called_once_with(self.order, 'pending', 'shipped')


class CheckoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            brand='Test Brand',
            category=self.category,
            price=100.00,
            stock=10
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        PaymentSettings.objects.create(
            razorpay_key_id='test_key',
            razorpay_key_secret='test_secret',
            is_active=True,
            currency='INR',
            currency_symbol='₹'
        )

    def test_checkout_requires_login(self):
        response = self.client.get('/orders/checkout', follow=False)
        self.assertIn(response.status_code, [301, 302])

    def test_checkout_empty_cart_redirects(self):
        self.client.login(username='testuser', password='testpass123')
        Cart.objects.filter(user=self.user).delete()
        response = self.client.get('/orders/checkout', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_checkout_view_status(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/orders/checkout', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'checkout.html')
        self.assertContains(response, 'id="pay-btn"')
        self.assertContains(response, 'PAY NOW')

    def test_checkout_response_sets_correlation_id_header(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/orders/checkout', HTTP_X_REQUEST_ID='req-test-123', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Request-ID'], 'req-test-123')

    def test_checkout_with_cart(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/orders/checkout', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('cart', response.context)

    def test_ajax_checkout_returns_razorpay_payload(self):
        self.client.login(username='testuser', password='testpass123')

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            client_cls.return_value.order.create.return_value = {
                'id': 'order_ajax_123',
                'amount': 20000,
                'currency': 'INR',
                'status': 'created',
            }

            response = self.client.post(
                reverse('orders:checkout'),
                {
                    'customer_name': 'Test User',
                    'email': 'test@example.com',
                    'phone_number': '9876543210',
                    'pincode': '560001',
                    'shipping_address': '123 Test Street',
                    'payment_method': 'razorpay',
                },
                HTTP_ACCEPT='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                'ok': True,
                'order_id': 1,
                'amount': 20000,
                'currency': 'INR',
                'razorpay_key': 'test_key',
                'razorpay_order_id': 'order_ajax_123',
                'verify_url': reverse('orders:verify_payment'),
                'failure_url': reverse('orders:payment_failure_callback'),
                'status_url': reverse('orders:order_status', args=[1]),
                'success_url': reverse('orders:order_success', args=[1]),
                'failed_url': reverse('orders:payment_failed') + '?order_id=1',
            },
        )

        order = Order.objects.get(user=self.user)
        self.assertEqual(order.razorpay_order_id, 'order_ajax_123')
        self.assertEqual(order.payment_status, 'pending')

    def test_checkout_persists_cart_items_as_order_items(self):
        second_product = Product.objects.create(
            name='Second Product',
            brand='Test Brand',
            category=self.category,
            price=80.00,
            stock=10,
        )
        CartItem.objects.create(
            cart=self.cart,
            product=second_product,
            quantity=1,
        )

        self.client.login(username='testuser', password='testpass123')

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            client_cls.return_value.order.create.return_value = {
                'id': 'order_items_123',
                'amount': 28000,
                'currency': 'INR',
                'status': 'created',
            }

            response = self.client.post(
                reverse('orders:checkout'),
                {
                    'customer_name': 'Test User',
                    'email': 'test@example.com',
                    'phone_number': '9876543210',
                    'pincode': '560001',
                    'shipping_address': '123 Test Street',
                    'payment_method': 'razorpay',
                },
                HTTP_ACCEPT='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )

        self.assertEqual(response.status_code, 200)

        order = Order.objects.get(user=self.user)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(
            set(order.items.values_list('product_id', 'quantity', 'price')),
            {
                (self.product.id, 2, self.product.price),
                (second_product.id, 1, second_product.price),
            },
        )
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())

    def test_checkout_post_renders_payment_page_with_csrf_form(self):
        self.client.login(username='testuser', password='testpass123')

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            client_cls.return_value.order.create.return_value = {
                'id': 'order_page_123',
                'amount': 20000,
                'currency': 'INR',
                'status': 'created',
            }

            response = self.client.post(
                reverse('orders:checkout'),
                {
                    'customer_name': 'Test User',
                    'email': 'test@example.com',
                    'phone_number': '9876543210',
                    'pincode': '560001',
                    'shipping_address': '123 Test Street',
                    'payment_method': 'razorpay',
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payment.html')
        self.assertContains(response, 'id="payment-csrf-form"')
        self.assertContains(response, 'getCsrfToken')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        RAZORPAY_KEY_ID='your_razorpay_key_id',
        RAZORPAY_KEY_SECRET='your_razorpay_key_secret',
    )
    def test_checkout_ignores_placeholder_razorpay_env_values_for_upi(self):
        PaymentSettings.objects.all().delete()
        PaymentSettings.objects.create(
            razorpay_key_id='',
            razorpay_key_secret='',
            is_active=False,
            upi_enabled=True,
            upi_id='upi@test',
            currency='INR',
            currency_symbol='₹'
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/orders/checkout/', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('razorpay', response.context['available_methods'])
        self.assertIn('upi', response.context['available_methods'])

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        RAZORPAY_KEY_ID='',
        RAZORPAY_KEY_SECRET='',
    )
    def test_checkout_with_upi_renders_upi_payment_page(self):
        PaymentSettings.objects.all().delete()
        PaymentSettings.objects.create(
            razorpay_key_id='',
            razorpay_key_secret='',
            is_active=False,
            upi_enabled=True,
            upi_id='upi@test',
            currency='INR',
            currency_symbol='₹'
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.post('/orders/checkout/', {
            'customer_name': 'UPI User',
            'email': 'upi@example.com',
            'phone_number': '9876543210',
            'pincode': '560001',
            'shipping_address': '123 Test Street',
            'payment_method': 'upi',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'upi_payment.html')
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        RAZORPAY_KEY_ID='',
        RAZORPAY_KEY_SECRET='',
    )
    def test_duplicate_checkout_submission_creates_only_one_order(self):
        PaymentSettings.objects.all().delete()
        PaymentSettings.objects.create(
            razorpay_key_id='',
            razorpay_key_secret='',
            is_active=False,
            upi_enabled=True,
            upi_id='upi@test',
            currency='INR',
            currency_symbol='â‚¹'
        )

        self.client.login(username='testuser', password='testpass123')
        payload = {
            'customer_name': 'UPI User',
            'email': 'upi@example.com',
            'phone_number': '9876543210',
            'pincode': '560001',
            'shipping_address': '123 Test Street',
            'payment_method': 'upi',
        }

        first_response = self.client.post('/orders/checkout/', payload, follow=True)
        second_response = self.client.post('/orders/checkout/', payload, follow=True)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())


class RazorpayPaymentFlowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='payuser', password='testpass123')
        self.client.login(username='payuser', password='testpass123')

    @override_settings(
        RAZORPAY_KEY_ID='env_key_id',
        RAZORPAY_KEY_SECRET='env_key_secret',
    )
    def test_verify_payment_uses_env_credentials_without_paymentsettings(self):
        PaymentSettings.objects.all().delete()
        order = Order.objects.create(
            user=self.user,
            total_price=250.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='pending',
            payment_status='pending',
            razorpay_order_id='order_env_123',
        )

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            client = client_cls.return_value
            client.utility.verify_payment_signature.return_value = None
            client.payment.fetch.return_value = {
                'id': 'pay_env_123',
                'order_id': 'order_env_123',
                'amount': 25000,
                'currency': 'INR',
                'status': 'captured',
                'captured': True,
            }

            response = self.client.post(
                reverse('orders:verify_payment'),
                {
                    'razorpay_order_id': 'order_env_123',
                    'razorpay_payment_id': 'pay_env_123',
                    'razorpay_signature': 'sig_env_123',
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('orders:order_status', args=[order.id]))
        client_cls.assert_called_once_with(auth=('env_key_id', 'env_key_secret'))

        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.razorpay_payment_id, 'pay_env_123')

        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.status, 'authorized')
        self.assertEqual(payment.razorpay_payment_id, 'pay_env_123')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='SYAFRA <noreply@syafra.com>',
        ORDER_ALERT_EMAILS=['ops@syafra.com'],
    )
    def test_verify_payment_returns_json_for_ajax_handler(self):
        PaymentSettings.objects.create(
            razorpay_key_id='test_key',
            razorpay_key_secret='test_secret',
            is_active=True,
            currency='INR',
            currency_symbol='₹',
        )
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='pending',
            payment_status='pending',
            razorpay_order_id='order_json_123',
        )

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            client = client_cls.return_value
            client.utility.verify_payment_signature.return_value = None
            client.payment.fetch.return_value = {
                'id': 'pay_json_123',
                'order_id': 'order_json_123',
                'amount': 10000,
                'currency': 'INR',
                'status': 'captured',
                'captured': True,
            }

            response = self.client.post(
                reverse('orders:verify_payment'),
                data=json.dumps({
                    'razorpay_order_id': 'order_json_123',
                    'razorpay_payment_id': 'pay_json_123',
                    'razorpay_signature': 'sig_json_123',
                }),
                content_type='application/json',
                HTTP_ACCEPT='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                'ok': True,
                'redirect_url': reverse('orders:order_status', args=[order.id]),
                'message': 'Payment received. Waiting for confirmation.',
                'order_id': order.id,
            },
        )

        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.status, 'pending')
        self.assertFalse(any(
            message.subject == f'Order Confirmation - Order #{order.id}'
            and 'pay@example.com' in message.to
            for message in mail.outbox
        ))

    def test_verify_payment_returns_already_paid_when_order_is_locked(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='paid',
            payment_status='paid',
            razorpay_order_id='order_paid_123',
            razorpay_payment_id='pay_locked_123',
        )

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            response = self.client.post(
                reverse('orders:verify_payment'),
                data=json.dumps({
                    'razorpay_order_id': 'order_paid_123',
                    'razorpay_payment_id': 'pay_locked_123',
                    'razorpay_signature': 'sig_locked_123',
                }),
                content_type='application/json',
                HTTP_ACCEPT='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                'ok': True,
                'redirect_url': reverse('orders:order_success', args=[order.id]),
                'message': 'Already paid',
                'order_id': order.id,
            },
        )
        client_cls.assert_not_called()

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='SYAFRA <noreply@syafra.com>',
        ORDER_ALERT_EMAILS=['ops@syafra.com'],
    )
    def test_verify_payment_uses_payment_attempt_when_order_has_new_retry_id(self):
        PaymentSettings.objects.create(
            razorpay_key_id='test_key',
            razorpay_key_secret='test_secret',
            is_active=True,
            currency='INR',
            currency_symbol='â‚¹',
        )
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='pending',
            payment_status='pending',
            razorpay_order_id='order_retry_current_123',
        )
        Payment.objects.create(
            order=order,
            provider='razorpay',
            status='created',
            amount=100.00,
            currency='INR',
            receipt=f'order_{order.id}_retry_old',
            razorpay_order_id='order_retry_old_123',
        )

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            client = client_cls.return_value
            client.utility.verify_payment_signature.return_value = None
            client.payment.fetch.return_value = {
                'id': 'pay_retry_old_123',
                'order_id': 'order_retry_old_123',
                'amount': 10000,
                'currency': 'INR',
                'status': 'captured',
                'captured': True,
            }

            response = self.client.post(
                reverse('orders:verify_payment'),
                data=json.dumps({
                    'razorpay_order_id': 'order_retry_old_123',
                    'razorpay_payment_id': 'pay_retry_old_123',
                    'razorpay_signature': 'sig_retry_old_123',
                }),
                content_type='application/json',
                HTTP_ACCEPT='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                'ok': True,
                'redirect_url': reverse('orders:order_status', args=[order.id]),
                'message': 'Payment received. Waiting for confirmation.',
                'order_id': order.id,
            },
        )

        order.refresh_from_db()
        self.assertEqual(order.razorpay_order_id, 'order_retry_current_123')
        self.assertEqual(order.razorpay_payment_id, 'pay_retry_old_123')

        payment = Payment.objects.get(order=order, razorpay_order_id='order_retry_old_123')
        self.assertEqual(payment.status, 'authorized')
        self.assertEqual(payment.razorpay_payment_id, 'pay_retry_old_123')

    def test_payment_failure_callback_returns_json_redirect(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='pending',
            payment_status='pending',
            razorpay_order_id='order_failed_123',
        )

        response = self.client.post(
            reverse('orders:payment_failure_callback'),
            data=json.dumps({
                'order_id': str(order.id),
                'razorpay_order_id': 'order_failed_123',
                'failure_reason': 'Payment failed at Razorpay checkout.',
            }),
            content_type='application/json',
            HTTP_ACCEPT='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                'ok': False,
                'redirect_url': reverse('orders:payment_failed') + f'?order_id={order.id}',
                'message': 'Payment was not completed. You can retry the payment below.',
            },
        )

        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'failed')
        self.assertEqual(order.status, 'failed')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='SYAFRA <noreply@syafra.com>',
        ORDER_ALERT_EMAILS=['ops@syafra.com'],
        RAZORPAY_WEBHOOK_SECRET='mysecret123',
    )
    def test_razorpay_webhook_marks_order_paid(self):
        PaymentSettings.objects.create(
            razorpay_key_id='test_key',
            razorpay_key_secret='test_secret',
            is_active=True,
            currency='INR',
            currency_symbol='₹',
        )
        category = Category.objects.create(name='Webhook Category', slug='webhook-category')
        product = Product.objects.create(
            name='Webhook Product',
            brand='Webhook Brand',
            category=category,
            price=100.00,
            stock=10,
        )
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='pending',
            payment_status='pending',
            razorpay_order_id='order_webhook_paid_123',
        )
        OrderItem.objects.create(order=order, product=product, quantity=1, price=100.00)

        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_webhook_paid_123',
                        'order_id': 'order_webhook_paid_123',
                        'currency': 'INR',
                        'status': 'captured',
                    }
                }
            }
        }
        body = json.dumps(payload).encode('utf-8')
        signature = hmac.new(b'mysecret123', body, hashlib.sha256).hexdigest()

        response = self.client.post(
            reverse('orders:razorpay_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.razorpay_payment_id, 'pay_webhook_paid_123')
        self.assertEqual(product.stock, 9)
        self.assertTrue(any(
            message.subject == f'Order Confirmed - Order #{order.id}'
            and 'pay@example.com' in message.to
            for message in mail.outbox
        ))

    @override_settings(
        RAZORPAY_WEBHOOK_SECRET='mysecret123',
    )
    def test_razorpay_webhook_marks_order_failed(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='pending',
            payment_status='pending',
            razorpay_order_id='order_webhook_failed_123',
        )

        payload = {
            'event': 'payment.failed',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_webhook_failed_123',
                        'order_id': 'order_webhook_failed_123',
                        'currency': 'INR',
                        'status': 'failed',
                        'error_description': 'Payment failed from webhook.',
                    }
                }
            }
        }
        body = json.dumps(payload).encode('utf-8')
        signature = hmac.new(b'mysecret123', body, hashlib.sha256).hexdigest()

        response = self.client.post(
            reverse('orders:razorpay_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'failed')
        self.assertEqual(order.status, 'failed')

    @override_settings(
        RAZORPAY_WEBHOOK_SECRET='mysecret123',
    )
    def test_razorpay_webhook_ignores_duplicate_paid_capture(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='paid',
            payment_status='paid',
            razorpay_order_id='order_webhook_duplicate_123',
            razorpay_payment_id='pay_webhook_duplicate_123',
            stock_reduced=True,
        )
        Payment.objects.create(
            order=order,
            provider='razorpay',
            status='paid',
            amount=100.00,
            currency='INR',
            receipt=f'order_{order.id}',
            razorpay_order_id='order_webhook_duplicate_123',
            razorpay_payment_id='pay_webhook_duplicate_123',
        )

        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_webhook_duplicate_123',
                        'order_id': 'order_webhook_duplicate_123',
                        'currency': 'INR',
                        'status': 'captured',
                    }
                }
            }
        }
        body = json.dumps(payload).encode('utf-8')
        signature = hmac.new(b'mysecret123', body, hashlib.sha256).hexdigest()

        response = self.client.post(
            reverse('orders:razorpay_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.razorpay_payment_id, 'pay_webhook_duplicate_123')
        self.assertEqual(
            Payment.objects.filter(order=order, razorpay_payment_id='pay_webhook_duplicate_123').count(),
            1,
        )

    @override_settings(
        RAZORPAY_WEBHOOK_SECRET='mysecret123',
    )
    def test_razorpay_webhook_failed_does_not_regress_paid_order(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='paid',
            payment_status='paid',
            razorpay_order_id='order_webhook_paid_456',
            razorpay_payment_id='pay_webhook_paid_456',
            stock_reduced=True,
        )
        Payment.objects.create(
            order=order,
            provider='razorpay',
            status='paid',
            amount=100.00,
            currency='INR',
            receipt=f'order_{order.id}',
            razorpay_order_id='order_webhook_paid_456',
            razorpay_payment_id='pay_webhook_paid_456',
        )

        payload = {
            'event': 'payment.failed',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_webhook_paid_456',
                        'order_id': 'order_webhook_paid_456',
                        'currency': 'INR',
                        'status': 'failed',
                        'error_description': 'Late failed webhook should not regress a paid order.',
                    }
                }
            }
        }
        body = json.dumps(payload).encode('utf-8')
        signature = hmac.new(b'mysecret123', body, hashlib.sha256).hexdigest()

        response = self.client.post(
            reverse('orders:razorpay_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.payment_status, 'paid')

        payment = Payment.objects.get(order=order, razorpay_payment_id='pay_webhook_paid_456')
        self.assertEqual(payment.status, 'paid')

    def test_order_status_renders_success_template_for_paid_orders(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='paid',
            payment_status='paid',
        )

        response = self.client.get(reverse('orders:order_status', args=[order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'success.html')
        self.assertContains(response, 'Payment Successful')

    def test_order_status_renders_failed_template_for_failed_orders(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='failed',
            payment_status='failed',
        )

        response = self.client.get(reverse('orders:order_status', args=[order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'failed.html')
        self.assertContains(response, 'Payment Failed')

    def test_order_status_renders_processing_template_for_pending_orders(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='pending',
            payment_status='pending',
        )

        response = self.client.get(reverse('orders:order_status', args=[order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'processing.html')
        self.assertContains(response, 'Continue Shopping')

    def test_order_status_response_is_never_cached(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Pay User',
            email='pay@example.com',
            phone_number='9876543210',
            shipping_address='123 Payment Street',
            status='pending',
            payment_status='pending',
        )

        response = self.client.get(reverse('orders:order_status', args=[order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertIn('no-cache', response['Cache-Control'])


class OrderSuccessViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.order = Order.objects.create(
            user=self.user,
            total_price=200.00,
            customer_name='John Doe',
            email='john@example.com',
            phone_number='1234567890',
            shipping_address='123 Test St',
            status='paid',
            payment_status='paid',
        )

    def test_order_success_requires_login(self):
        response = self.client.get(f'/orders/success/{self.order.id}/', follow=False)
        self.assertIn(response.status_code, [301, 302])

    def test_order_success_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/orders/success/{self.order.id}/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'success.html')
        self.assertEqual(response.context['order'], self.order)
        self.assertIn('no-cache', response['Cache-Control'])

    def test_order_success_redirects_unpaid_orders_to_status_page(self):
        self.order.status = 'pending'
        self.order.payment_status = 'pending'
        self.order.save(update_fields=['status', 'payment_status'])

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/orders/success/{self.order.id}/', follow=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('orders:order_status', args=[self.order.id]))

    def test_order_success_other_user_404(self):
        other_user = User.objects.create_user(username='otheruser', password='testpass123')
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(f'/orders/success/{self.order.id}/', follow=True)
        self.assertEqual(response.status_code, 404)


class OrderHistoryViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.order = Order.objects.create(
            user=self.user,
            total_price=200.00,
            customer_name='John Doe',
            email='john@example.com',
            phone_number='1234567890',
            shipping_address='123 Test St'
        )

    def test_order_history_requires_login(self):
        response = self.client.get('/orders/history/', follow=False)
        self.assertIn(response.status_code, [301, 302])

    def test_order_history_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/orders/history/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'order_history.html')
        self.assertIn(self.order, response.context['orders'])


class OrderDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            brand='Test Brand',
            category=self.category,
            price=100.00,
            stock=10
        )
        self.order = Order.objects.create(
            user=self.user,
            total_price=200.00,
            customer_name='John Doe',
            email='john@example.com',
            phone_number='1234567890',
            shipping_address='123 Test St'
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=100.00
        )

    def test_order_detail_requires_login(self):
        response = self.client.get(f'/orders/detail/{self.order.id}/', follow=False)
        self.assertIn(response.status_code, [301, 302])

    def test_order_detail_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/orders/detail/{self.order.id}/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'order_detail.html')
        self.assertEqual(response.context['order'], self.order)
        self.assertEqual(response.context['items'].count(), 1)


class OrderFlowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='flowuser', password='testpass123')
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Flow Product',
            brand='Flow Brand',
            category=self.category,
            price=100.00,
            stock=10
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        RAZORPAY_KEY_ID='',
        RAZORPAY_KEY_SECRET='',
    )
    def test_checkout_fails_when_no_payment_methods_available(self):
        PaymentSettings.objects.create(
            razorpay_key_id='',
            razorpay_key_secret='',
            is_active=True,
            currency='INR',
            currency_symbol='₹'
        )
        self.client.login(username='flowuser', password='testpass123')

        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Online payment is temporarily unavailable')

    def test_packed_transition_for_paid_order_sends_status_event_email(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
        )

        from orders.services.email_service import send_order_status_email_if_changed

        with mock.patch('orders.services.email_service.send_order_email', return_value=True) as email_mock:
            sent = send_order_status_email_if_changed(order, 'paid', 'packed')

        self.assertTrue(sent)
        email_mock.assert_called_once_with(order, 'confirmed')

    def test_order_creation_model_save_does_not_send_customer_email_from_signal(self):
        with mock.patch('orders.services.email_service.send_order_email') as email_mock:
            Order.objects.create(
                user=self.user,
                total_price=100.00,
                customer_name='Jane Doe',
                email='jane@example.com',
                phone_number='9876543210',
                shipping_address='123 Flow Lane',
                status='pending',
                payment_status='pending',
            )

        email_mock.assert_not_called()

    def test_paid_confirmation_transition_reduces_stock_and_sends_status_email_directly(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

        from orders.services.order_service import confirm_order_payment

        with mock.patch('orders.services.email_service.send_order_status_email_if_changed', return_value=True) as status_email_mock:
            confirmed_order, processed = confirm_order_payment(order, payment_reference='PAY-123')

        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertTrue(processed)
        self.assertEqual(confirmed_order.status, 'paid')
        self.assertTrue(order.stock_reduced)
        self.assertEqual(self.product.stock, 9)
        status_email_mock.assert_called_once()
        _sent_order, old_status, new_status = status_email_mock.call_args.args
        self.assertEqual(old_status, 'pending')
        self.assertEqual(new_status, 'paid')

    def test_confirmation_email_queue_is_idempotent(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

        from orders.signals import queue_email_notification

        def mark_confirmation_sent(order_pk, email_type, status_override=None, correlation_id=None):
            Order.objects.filter(pk=order_pk).update(confirmation_email_sent=True)

        with mock.patch('orders.signals._send_email_instant', side_effect=mark_confirmation_sent) as instant_email:
            queue_email_notification(order, 'confirmation')
            queue_email_notification(order, 'confirmation')
            order.refresh_from_db()

        instant_email.assert_called_once()
        self.assertTrue(order.confirmation_email_sent)

    def test_email_queue_sends_immediately(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

        from orders.signals import queue_email_notification

        with mock.patch('orders.signals._send_email_instant', return_value=True) as instant_email:
            queue_email_notification(order, 'confirmation')

        instant_email.assert_called_once()

    def test_email_queue_uses_sync_send_path(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

        from orders.signals import queue_email_notification

        with mock.patch('orders.signals._send_email_instant', return_value=True) as instant_email:
            queue_email_notification(order, 'confirmation')
        instant_email.assert_called_once()

    def test_email_claim_is_released_after_failure_for_retry(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

        from orders.services.email_service import send_notification_email

        with mock.patch('orders.services.email_service.send_order_confirmation_email', return_value=False):
            self.assertFalse(send_notification_email(order.id, 'confirmation'))
        order.refresh_from_db()
        self.assertFalse(order.confirmation_email_sent)

        with mock.patch('orders.services.email_service.send_order_confirmation_email', return_value=True):
            self.assertTrue(send_notification_email(order.id, 'confirmation', raise_on_failure=True))
        order.refresh_from_db()
        self.assertTrue(order.confirmation_email_sent)

    def test_active_email_claim_blocks_duplicate_sender(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
            confirmation_email_claimed_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

        from orders.services.email_service import send_notification_email

        with mock.patch('orders.services.email_service.send_order_confirmation_email', return_value=True) as sender:
            self.assertFalse(send_notification_email(order.id, 'confirmation'))

        sender.assert_not_called()
        order.refresh_from_db()
        self.assertFalse(order.confirmation_email_sent)
        self.assertIsNotNone(order.confirmation_email_claimed_at)

    @override_settings(ORDER_EMAIL_CLAIM_TIMEOUT_SECONDS=60)
    def test_stale_email_claim_is_recovered_after_timeout(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
            confirmation_email_claimed_at=timezone.now() - timedelta(minutes=5),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

        from orders.services.email_service import send_notification_email

        with mock.patch('orders.services.email_service.send_order_confirmation_email', return_value=True) as sender:
            self.assertTrue(send_notification_email(order.id, 'confirmation', raise_on_failure=True))

        sender.assert_called_once()
        order.refresh_from_db()
        self.assertTrue(order.confirmation_email_sent)
        self.assertIsNone(order.confirmation_email_claimed_at)

    def test_confirm_order_payment_is_idempotent(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

        from orders.services.order_service import confirm_order_payment

        confirmed_order, processed = confirm_order_payment(order, payment_reference='UPI-TXN-1')
        self.product.refresh_from_db()
        first_stock = self.product.stock

        duplicate_order, duplicate_processed = confirm_order_payment(order, payment_reference='UPI-TXN-1')
        self.product.refresh_from_db()

        self.assertTrue(processed)
        self.assertFalse(duplicate_processed)
        self.assertEqual(first_stock, 9)
        self.assertEqual(self.product.stock, 9)
        self.assertEqual(confirmed_order.razorpay_payment_id, 'UPI-TXN-1')
        self.assertEqual(duplicate_order.razorpay_payment_id, 'UPI-TXN-1')

    def test_payment_reference_must_be_unique_when_present(self):
        Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='First',
            email='first@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            razorpay_payment_id='PAY-123',
        )

        with self.assertRaises(IntegrityError):
            Order.objects.create(
                user=self.user,
                total_price=100.00,
                customer_name='Second',
                email='second@example.com',
                phone_number='9876543211',
                shipping_address='456 Flow Lane',
                razorpay_payment_id='PAY-123',
            )

    def test_send_whatsapp_notification_task_calls_service(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending'
        )

        with mock.patch('orders.tasks.send_whatsapp_message', return_value=True) as send_whatsapp:
            from .tasks import send_whatsapp_notification
            result = send_whatsapp_notification.run(order.id, 'shipped')
            self.assertTrue(result)
            send_whatsapp.assert_called_once_with(order, 'shipped')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        RAZORPAY_KEY_ID='',
        RAZORPAY_KEY_SECRET='',
    )
    def test_upi_payment_verify_confirms_order(self):
        PaymentSettings.objects.create(
            razorpay_key_id='',
            razorpay_key_secret='',
            is_active=False,
            upi_enabled=True,
            upi_id='upi@test',
            currency='INR',
            currency_symbol='₹'
        )
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00
        )
        self.client.login(username='flowuser', password='testpass123')

        response = self.client.post(reverse('orders:upi_payment_verify'), {
            'order_id': order.id,
            'transaction_id': 'TXN123456',
        }, follow=True)

        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'success.html')
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.razorpay_payment_id, 'UPI-TXN123456')
        self.assertTrue(order.stock_reduced)
        self.assertTrue(Payment.objects.filter(order=order, provider='upi', status='paid').exists())

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        RAZORPAY_KEY_ID='',
        RAZORPAY_KEY_SECRET='',
    )
    def test_upi_payment_verify_rejects_invalid_transaction_id(self):
        PaymentSettings.objects.create(
            razorpay_key_id='',
            razorpay_key_secret='',
            is_active=False,
            upi_enabled=True,
            upi_id='upi@test',
            currency='INR',
            currency_symbol='â‚¹'
        )
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00
        )
        self.client.login(username='flowuser', password='testpass123')

        response = self.client.post(reverse('orders:upi_payment_verify'), {
            'order_id': order.id,
            'transaction_id': 'bad txn!',
        }, follow=True)

        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_status, 'pending')
        self.assertFalse(order.stock_reduced)

    def test_retry_payment_generates_new_gateway_order_for_failed_order(self):
        PaymentSettings.objects.create(
            razorpay_key_id='test_key',
            razorpay_key_secret='test_secret',
            is_active=True,
            currency='INR',
            currency_symbol='â‚¹'
        )
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='failed',
            payment_status='failed',
            razorpay_order_id='order_existing_123',
            razorpay_payment_id='pay_existing_123',
        )
        Payment.objects.create(
            order=order,
            provider='razorpay',
            status='failed',
            amount=100.00,
            currency='INR',
            receipt=f'order_{order.id}_failed',
            razorpay_order_id='order_existing_123',
            razorpay_payment_id='pay_existing_123',
            failure_reason='Previous attempt failed.',
        )
        self.client.login(username='flowuser', password='testpass123')

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            client_cls.return_value.order.create.return_value = {'id': 'order_retry_fresh_123'}
            response = self.client.get(reverse('orders:retry_payment', args=[order.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'retry_payment.html')
        self.assertEqual(response.context['razorpay_order_id'], 'order_retry_fresh_123')
        client_cls.return_value.order.create.assert_called_once()

        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.razorpay_order_id, 'order_retry_fresh_123')
        self.assertEqual(order.razorpay_payment_id, '')
        self.assertIsNotNone(order.payment_retry_reserved_at)
        self.assertTrue(Payment.objects.filter(order=order, razorpay_order_id='order_existing_123').exists())
        self.assertTrue(Payment.objects.filter(order=order, razorpay_order_id='order_retry_fresh_123').exists())

    def test_retry_payment_replaces_expired_retry_session(self):
        PaymentSettings.objects.create(
            razorpay_key_id='test_key',
            razorpay_key_secret='test_secret',
            is_active=True,
            currency='INR',
            currency_symbol='â‚¹'
        )
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
            razorpay_order_id='order_retry_old',
            payment_retry_reserved_at=timezone.now() - timedelta(hours=2),
        )
        self.client.login(username='flowuser', password='testpass123')

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            client_cls.return_value.order.create.return_value = {'id': 'order_retry_new'}
            response = self.client.get(reverse('orders:retry_payment', args=[order.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'retry_payment.html')
        self.assertEqual(response.context['razorpay_order_id'], 'order_retry_new')
        order.refresh_from_db()
        self.assertEqual(order.razorpay_order_id, 'order_retry_new')
        self.assertIsNotNone(order.payment_retry_reserved_at)

    def test_retry_payment_blocks_duplicate_reservation(self):
        PaymentSettings.objects.create(
            razorpay_key_id='test_key',
            razorpay_key_secret='test_secret',
            is_active=True,
            currency='INR',
            currency_symbol='â‚¹'
        )
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending',
            payment_status='pending',
            razorpay_order_id='retry_res_1_existingreservation',
            payment_retry_reserved_at=timezone.now(),
        )
        self.client.login(username='flowuser', password='testpass123')

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            response = self.client.get(reverse('orders:retry_payment', args=[order.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context['order_id']), str(order.id))
        client_cls.return_value.order.create.assert_not_called()

    def test_retry_payment_redirects_paid_order_without_creating_new_gateway_order(self):
        PaymentSettings.objects.create(
            razorpay_key_id='test_key',
            razorpay_key_secret='test_secret',
            is_active=True,
            currency='INR',
            currency_symbol='Ã¢â€šÂ¹'
        )
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='paid',
            payment_status='paid',
            razorpay_order_id='order_paid_existing',
            razorpay_payment_id='pay_paid_existing',
            stock_reduced=True,
        )
        self.client.login(username='flowuser', password='testpass123')

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            response = self.client.get(reverse('orders:retry_payment', args=[order.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'success.html')
        client_cls.assert_not_called()

    def test_inventory_lock_order_is_deterministic(self):
        second_product = Product.objects.create(
            name='Flow Product 2',
            brand='Flow Brand',
            category=self.category,
            price=80.00,
            stock=10,
        )
        first_item = OrderItem(order=Order(user=self.user), product=second_product, quantity=1, price=80.00, size='XL')
        second_item = OrderItem(order=Order(user=self.user), product=self.product, quantity=1, price=100.00, size='M')
        third_item = OrderItem(order=Order(user=self.user), product=self.product, quantity=1, price=100.00, size='')

        from orders.services.order_service import sort_inventory_items

        ordered = sort_inventory_items([first_item, second_item, third_item])
        ordered_keys = [(item.product_id, item.size or '') for item in ordered]

        self.assertEqual(
            ordered_keys,
            [
                (self.product.id, ''),
                (self.product.id, 'M'),
                (second_product.id, 'XL'),
            ],
        )
