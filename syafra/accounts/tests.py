from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

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
