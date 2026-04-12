import base64
import json
import time
from unittest import mock

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.utils import timezone
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import EmailLog, EmailWebhookEvent
from accounts.utils.email import send_email
from orders.models import Order

User = get_user_model()


class RegisterViewTest(TestCase):
    def test_register_view_get(self):
        response = self.client.get('/accounts/register', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_register_view_authenticated_redirect(self):
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/accounts/register', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_register_success(self):
        # Must satisfy Django AUTH_PASSWORD_VALIDATORS (e.g. not too common / too similar).
        strong_pw = 'Nw7!kQ9pLx2#vR4mB8'
        response = self.client.post('/accounts/register/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': strong_pw,
            'password2': strong_pw,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')

    def test_register_password_mismatch(self):
        response = self.client.post('/accounts/register/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'Nw7!kQ9pLx2#vR4mB8',
            'password2': 'DifferentStr0ng!Pw',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username='existinguser', password='testpass123')
        pw = 'Nw7!kQ9pLx2#vR4mB8'
        response = self.client.post('/accounts/register/', {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password': pw,
            'password2': pw,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username already exists.', html=True)
        self.assertFalse(User.objects.filter(email='new@example.com').exists())
    
    def test_register_duplicate_email(self):
        User.objects.create_user(username='existinguser', email='existing@example.com', password='testpass123')
        pw = 'Nw7!kQ9pLx2#vR4mB8'
        response = self.client.post('/accounts/register/', {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password': pw,
            'password2': pw,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email already registered.', html=True)
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_register_password_too_short(self):
        response = self.client.post('/accounts/register/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'short',
            'password2': 'short',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
    
    def test_register_empty_fields(self):
        response = self.client.post('/accounts/register/', {
            'username': '',
            'email': '',
            'password': '',
            'password2': '',
        }, follow=True)
        self.assertEqual(response.status_code, 200)


class LoginViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_login_view_get(self):
        response = self.client.get('/accounts/login', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_view_authenticated_redirect(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/accounts/login', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_login_invalid_credentials(self):
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'wrongpassword',
        }, follow=True)
        self.assertEqual(response.status_code, 200)


class LogoutViewTest(TestCase):
    def test_logout_post(self):
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('accounts:logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_logout_get_not_allowed(self):
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 405)


class ProfileViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_profile_view_requires_login(self):
        response = self.client.get('/accounts/profile', follow=False)
        self.assertIn(response.status_code, [301, 302])

    def test_profile_view_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/accounts/profile', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')
        self.assertEqual(response.context['user'], self.user)

    def test_profile_view_shows_orders(self):
        from orders.models import Order
        Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Test User',
            email='test@example.com',
            phone_number='1234567890',
            shipping_address='Test Address'
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/accounts/profile', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['orders']), 1)


@override_settings(
    EMAIL_BACKEND='sendgrid_sdk',
    SENDGRID_API_KEY='SG.test-key',
    SENDGRID_SENDER_EMAIL='noreply@syafra.com',
    DEFAULT_FROM_EMAIL='SYAFRA <noreply@syafra.com>',
    EMAIL_SIMPLE_RETRY_BASE_DELAY_SECONDS=0,
)
class EmailInfrastructureTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='emailuser',
            email='emailuser@example.com',
            password='testpass123',
        )
        self.order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            customer_name='Email User',
            email='emailuser@example.com',
            phone_number='9876543210',
            shipping_address='123 Email Street',
            status='paid',
            payment_status='paid',
        )

    @mock.patch('accounts.utils.email.SendGridAPIClient')
    @override_settings(EMAIL_SIMPLE_RETRY_ATTEMPTS=1)
    def test_send_email_creates_accepted_email_log(self, client_cls):
        client = client_cls.return_value
        client.send.return_value = mock.Mock(
            status_code=202,
            body=b'',
            headers={'X-Message-Id': 'msg-123'},
        )

        sent = send_email(
            subject='Account activation',
            message='Activate your account',
            recipient_list=['customer@example.com'],
            email_type='account_activation',
            user=self.user,
            order=self.order,
            metadata={'flow': 'test'},
        )

        self.assertTrue(sent)
        email_log = EmailLog.objects.get()
        self.assertEqual(email_log.status, EmailLog.STATUS_ACCEPTED)
        self.assertEqual(email_log.sendgrid_message_id, 'msg-123')
        self.assertEqual(email_log.send_attempts, 1)
        self.assertEqual(email_log.user, self.user)
        self.assertEqual(email_log.order, self.order)

    @mock.patch('accounts.utils.email.SendGridAPIClient')
    @override_settings(EMAIL_SIMPLE_RETRY_ATTEMPTS=1)
    def test_send_email_marks_retryable_failure(self, client_cls):
        client = client_cls.return_value
        client.send.return_value = mock.Mock(
            status_code=500,
            body=b'{"errors":[{"message":"temporary upstream error"}]}',
            headers={},
        )

        sent = send_email(
            subject='Payment confirmation',
            message='Your payment is confirmed',
            recipient_list=['customer@example.com'],
            email_type='payment_confirmation',
            user=self.user,
            order=self.order,
        )

        self.assertFalse(sent)
        email_log = EmailLog.objects.get()
        self.assertEqual(email_log.status, EmailLog.STATUS_FAILED)
        self.assertTrue(email_log.retryable)
        self.assertEqual(email_log.sendgrid_response_status, 500)
        self.assertIn('temporary upstream error', email_log.provider_response)

    @override_settings(EMAIL_SIMPLE_RETRY_ATTEMPTS=1)
    def test_sendgrid_webhook_updates_email_log(self):
        email_log = EmailLog.objects.create(
            email_type=EmailLog.TYPE_ORDER_CONFIRMATION,
            user=self.user,
            order=self.order,
            recipient='customer@example.com',
            recipient_domain='example.com',
            subject='Order confirmation',
            status=EmailLog.STATUS_ACCEPTED,
            sendgrid_message_id='msg-accepted',
        )

        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode('utf-8')
        public_key_value = ''.join(
            line for line in public_key.splitlines() if 'BEGIN PUBLIC KEY' not in line and 'END PUBLIC KEY' not in line
        )

        payload = json.dumps(
            [
                {
                    'event': 'delivered',
                    'email': 'customer@example.com',
                    'timestamp': 1_710_000_000,
                    'sg_event_id': 'evt-123',
                    'sg_message_id': 'msg-accepted',
                    'custom_args': {
                        'email_log_id': str(email_log.id),
                    },
                }
            ]
        )
        timestamp = str(int(time.time()))
        signature = private_key.sign(
            (timestamp + payload).encode('utf-8'),
            ec.ECDSA(hashes.SHA256()),
        )

        with self.settings(SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY=public_key_value):
            response = self.client.post(
                reverse('accounts:sendgrid_event_webhook'),
                data=payload,
                content_type='application/json',
                HTTP_X_TWILIO_EMAIL_EVENT_WEBHOOK_SIGNATURE=base64.b64encode(signature).decode('utf-8'),
                HTTP_X_TWILIO_EMAIL_EVENT_WEBHOOK_TIMESTAMP=timestamp,
            )

        self.assertEqual(response.status_code, 200)
        email_log.refresh_from_db()
        self.assertEqual(email_log.status, EmailLog.STATUS_DELIVERED)
        self.assertEqual(email_log.last_event_type, 'delivered')
        self.assertEqual(EmailWebhookEvent.objects.count(), 1)

    def test_open_event_keeps_delivery_status_and_increments_open_count(self):
        from accounts.email_tracking import apply_sendgrid_webhook_event

        email_log = EmailLog.objects.create(
            email_type=EmailLog.TYPE_ORDER_CONFIRMATION,
            user=self.user,
            order=self.order,
            recipient='customer@example.com',
            recipient_domain='example.com',
            subject='Order confirmation',
            status=EmailLog.STATUS_DELIVERED,
            sendgrid_message_id='msg-opened',
            delivered_at=timezone.now(),
        )

        apply_sendgrid_webhook_event(
            {
                'event': 'open',
                'email': 'customer@example.com',
                'timestamp': 1_710_000_100,
                'sg_event_id': 'evt-open-1',
                'sg_message_id': 'msg-opened',
                'custom_args': {
                    'email_log_id': str(email_log.id),
                },
            }
        )

        email_log.refresh_from_db()
        self.assertEqual(email_log.status, EmailLog.STATUS_DELIVERED)
        self.assertEqual(email_log.open_count, 1)
        self.assertIsNotNone(email_log.opened_at)

    def test_blocked_event_updates_blocked_timestamp(self):
        from accounts.email_tracking import apply_sendgrid_webhook_event

        email_log = EmailLog.objects.create(
            email_type=EmailLog.TYPE_ORDER_CONFIRMATION,
            user=self.user,
            order=self.order,
            recipient='customer@example.com',
            recipient_domain='example.com',
            subject='Order confirmation',
            status=EmailLog.STATUS_ACCEPTED,
            sendgrid_message_id='msg-blocked',
        )

        apply_sendgrid_webhook_event(
            {
                'event': 'blocked',
                'email': 'customer@example.com',
                'timestamp': 1_710_000_200,
                'sg_event_id': 'evt-blocked-1',
                'sg_message_id': 'msg-blocked',
                'response': 'Blocked due to recipient policy.',
                'custom_args': {
                    'email_log_id': str(email_log.id),
                },
            }
        )

        email_log.refresh_from_db()
        self.assertEqual(email_log.status, EmailLog.STATUS_BLOCKED)
        self.assertEqual(email_log.error_message, 'Blocked due to recipient policy.')
        self.assertIsNotNone(email_log.blocked_at)
