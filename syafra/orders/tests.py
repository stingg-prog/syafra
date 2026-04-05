from datetime import timedelta

from django.core import mail
from django.test import TestCase, Client, override_settings
from django.db import IntegrityError
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest import mock
from products.models import Category, Product
from cart.models import Cart, CartItem
from .models import Order, OrderItem, PaymentSettings

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
            shipping_address='123 Test St'
        )

    def test_order_success_requires_login(self):
        response = self.client.get(f'/orders/success/{self.order.id}/', follow=False)
        self.assertIn(response.status_code, [301, 302])

    def test_order_success_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/orders/success/{self.order.id}/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'order_success.html')
        self.assertEqual(response.context['order'], self.order)

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

    def test_order_status_change_admin_action_queues_notifications(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='pending'
        )

        with mock.patch('orders.signals.queue_email_notification') as email_mock, mock.patch('orders.signals.queue_whatsapp_notification') as whatsapp_mock:
            order.status = 'confirmed'
            order.save()

            email_mock.assert_called_once_with(order, 'status', status_override='confirmed')
            whatsapp_mock.assert_called_once_with(order, 'processing')

    def test_pending_order_creation_does_not_queue_customer_email(self):
        with mock.patch('orders.signals.queue_email_notification') as email_mock:
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

    def test_paid_confirmation_transition_reduces_stock_and_queues_both_emails(self):
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

        with mock.patch('orders.signals.queue_email_notification') as email_mock, mock.patch('orders.signals.queue_whatsapp_notification') as whatsapp_mock:
            order.status = 'confirmed'
            order.payment_status = 'paid'
            order.save()

        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertTrue(order.stock_reduced)
        self.assertEqual(self.product.stock, 9)
        email_mock.assert_any_call(order, 'confirmation')
        email_mock.assert_any_call(order, 'payment')
        whatsapp_mock.assert_called_once_with(order, 'created')

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
            with self.captureOnCommitCallbacks(execute=True):
                queue_email_notification(order, 'confirmation')
                queue_email_notification(order, 'confirmation')
            order.refresh_from_db()

        instant_email.assert_called_once()
        self.assertTrue(order.confirmation_email_sent)

    def test_email_queue_falls_back_to_sync_when_async_dispatch_fails(self):
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Jane Doe',
            email='jane@example.com',
            phone_number='9876543210',
            shipping_address='123 Flow Lane',
            status='confirmed',
            payment_status='paid',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=1,
            price=100.00,
        )

        from orders.signals import queue_email_notification

        with mock.patch('orders.signals._send_email_instant', return_value=True) as instant_email:
            with self.captureOnCommitCallbacks(execute=True):
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
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.razorpay_payment_id, 'UPI-TXN123456')
        self.assertTrue(order.stock_reduced)

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

    def test_retry_payment_reuses_existing_gateway_order(self):
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
            razorpay_order_id='order_existing_123',
        )
        self.client.login(username='flowuser', password='testpass123')

        with mock.patch('orders.views.razorpay.Client') as client_cls:
            response = self.client.get(reverse('orders:retry_payment', args=[order.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'retry_payment.html')
        self.assertEqual(response.context['razorpay_order_id'], 'order_existing_123')
        client_cls.return_value.order.create.assert_not_called()

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
        self.assertEqual(response.context['order_id'], str(order.id))
        client_cls.return_value.order.create.assert_not_called()

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
