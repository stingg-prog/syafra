from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Category, Product
from orders.models import PaymentSettings
from .models import Cart, CartItem

User = get_user_model()


class CartModelTest(TestCase):
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

    def test_cart_creation(self):
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(cart.user, self.user)
        self.assertEqual(str(cart), f'Cart {cart.id} - {self.user.username}')

    def test_cart_total(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        self.assertEqual(cart.total, 200.00)

    def test_cart_item_subtotal(self):
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=3)
        self.assertEqual(cart_item.subtotal, 300.00)


class CartViewTest(TestCase):
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

    def test_cart_view_requires_login(self):
        response = self.client.get('/cart', follow=False)
        self.assertIn(response.status_code, [301, 302])

    def test_cart_view_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/cart', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart.html')

    def test_cart_view_allows_checkout_for_upi_only_configuration(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        PaymentSettings.objects.create(
            razorpay_key_id='',
            razorpay_key_secret='',
            is_active=False,
            upi_enabled=True,
            upi_id='upi@test',
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/cart', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['checkout_available'])
        self.assertContains(response, 'PROCEED TO CHECKOUT')


class AddToCartTest(TestCase):
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

    def test_add_to_cart_requires_login(self):
        response = self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': 1}
        )
        self.assertEqual(response.status_code, 302)

    def test_add_to_cart_success(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': 1}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 1)

    def test_add_to_cart_increases_quantity(self):
        self.client.login(username='testuser', password='testpass123')
        self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': 1}
        )
        self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': 2}
        )
        
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 3)

    def test_add_to_cart_exceeds_stock(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': 15}
        )
        self.assertEqual(response.status_code, 400)
    
    def test_add_to_cart_zero_quantity(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': 0}
        )
        self.assertEqual(response.status_code, 400)
    
    def test_add_to_cart_negative_quantity(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': -5}
        )
        self.assertEqual(response.status_code, 400)
    
    def test_add_to_cart_exact_stock(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            f'/cart/add/{self.product.id}/',
            {'quantity': 10}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])


class RemoveFromCartTest(TestCase):
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

    def test_remove_from_cart_requires_login(self):
        response = self.client.post(
            f'/cart/remove/{self.cart_item.id}/'
        )
        self.assertEqual(response.status_code, 302)

    def test_remove_from_cart_success(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            f'/cart/remove/{self.cart_item.id}/'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(CartItem.objects.count(), 0)


class UpdateCartItemTest(TestCase):
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

    def test_update_quantity_requires_login(self):
        response = self.client.post(
            f'/cart/update/{self.cart_item.id}/',
            {'quantity': 5}
        )
        self.assertEqual(response.status_code, 302)

    def test_update_quantity_success(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            f'/cart/update/{self.cart_item.id}/',
            {'quantity': 5}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.cart_item.refresh_from_db()
        self.assertEqual(self.cart_item.quantity, 5)

    def test_update_quantity_to_zero_removes_item(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            f'/cart/update/{self.cart_item.id}/',
            {'quantity': 0}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['item_removed'])
        self.assertEqual(CartItem.objects.count(), 0)

    def test_update_quantity_exceeds_stock(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            f'/cart/update/{self.cart_item.id}/',
            {'quantity': 15}
        )
        self.assertEqual(response.status_code, 400)


class CartContextProcessorTest(TestCase):
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

    def test_cart_context_not_logged_in(self):
        from cart.context_processors import cart_context
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = type('AnonymousUser', (), {'is_authenticated': False})()
        
        context = cart_context(request)
        self.assertEqual(context['cart_count'], 0)

    def test_cart_context_logged_in(self):
        from cart.context_processors import cart_context
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        
        context = cart_context(request)
        self.assertEqual(context['cart_count'], 1)
