import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from products.models import Category, Product
from .models import Wishlist

User = get_user_model()


class WishlistTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='wishlister', password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category', slug='test-category'
        )
        self.product = Product.objects.create(
            name='Wishlist Product',
            brand='Test Brand',
            category=self.category,
            price=50.00,
            stock=10,
        )
        self.product2 = Product.objects.create(
            name='Second Product',
            brand='Test Brand',
            category=self.category,
            price=30.00,
            stock=5,
        )


class WishlistAddTest(WishlistTestBase):
    def test_add_to_wishlist_requires_login(self):
        response = self.client.post(
            reverse('wishlist:add', args=[self.product.pk])
        )
        self.assertIn(response.status_code, [401, 403, 302])

    def test_add_to_wishlist_success(self):
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.post(
            reverse('wishlist:add', args=[self.product.pk])
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['wishlisted'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['message'], 'Added to wishlist.')
        self.assertTrue(
            Wishlist.objects.filter(user=self.user, product=self.product).exists()
        )

    def test_add_to_wishlist_duplicate(self):
        Wishlist.objects.create(user=self.user, product=self.product)
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.post(
            reverse('wishlist:add', args=[self.product.pk])
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['wishlisted'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['message'], 'Already in wishlist.')
        self.assertEqual(
            Wishlist.objects.filter(user=self.user, product=self.product).count(),
            1,
        )

    def test_add_to_wishlist_invalid_product(self):
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.post(reverse('wishlist:add', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_add_get_method_rejected(self):
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.get(reverse('wishlist:add', args=[self.product.pk]))
        self.assertEqual(response.status_code, 405)


class WishlistRemoveTest(WishlistTestBase):
    def test_remove_from_wishlist_requires_login(self):
        response = self.client.post(
            reverse('wishlist:remove', args=[self.product.pk])
        )
        self.assertIn(response.status_code, [401, 403, 302])

    def test_remove_from_wishlist_success(self):
        Wishlist.objects.create(user=self.user, product=self.product)
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.post(
            reverse('wishlist:remove', args=[self.product.pk])
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['wishlisted'])
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['message'], 'Removed from wishlist.')
        self.assertFalse(
            Wishlist.objects.filter(user=self.user, product=self.product).exists()
        )

    def test_remove_from_wishlist_not_in_wishlist(self):
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.post(
            reverse('wishlist:remove', args=[self.product.pk])
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['wishlisted'])
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['message'], 'Not in wishlist.')

    def test_remove_from_wishlist_invalid_product(self):
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.post(reverse('wishlist:remove', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_remove_get_method_rejected(self):
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.get(
            reverse('wishlist:remove', args=[self.product.pk])
        )
        self.assertEqual(response.status_code, 405)


class WishlistStatusTest(WishlistTestBase):
    def test_status_requires_login(self):
        response = self.client.get(
            reverse('wishlist:status', args=[self.product.pk])
        )
        self.assertIn(response.status_code, [401, 403, 302])

    def test_status_wishlisted_true(self):
        Wishlist.objects.create(user=self.user, product=self.product)
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.get(
            reverse('wishlist:status', args=[self.product.pk])
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['wishlisted'])

    def test_status_wishlisted_false(self):
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.get(
            reverse('wishlist:status', args=[self.product.pk])
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['wishlisted'])

    def test_status_invalid_product(self):
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.get(reverse('wishlist:status', args=[9999]))
        self.assertEqual(response.status_code, 404)


class WishlistCountTest(WishlistTestBase):
    def test_count_requires_login(self):
        response = self.client.get(reverse('wishlist:count'))
        self.assertIn(response.status_code, [401, 403, 302])

    def test_count_zero(self):
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.get(reverse('wishlist:count'))
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 0)

    def test_count_multiple_items(self):
        Wishlist.objects.create(user=self.user, product=self.product)
        Wishlist.objects.create(user=self.user, product=self.product2)
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.get(reverse('wishlist:count'))
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 2)

    def test_count_only_owns_items(self):
        other = User.objects.create_user(
            username='other', password='testpass123'
        )
        Wishlist.objects.create(user=other, product=self.product)
        self.client.login(username='wishlister', password='testpass123')
        response = self.client.get(reverse('wishlist:count'))
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 0)


class WishlistAnonymousTest(WishlistTestBase):
    def test_all_endpoints_reject_anonymous(self):
        endpoints = [
            ('POST', reverse('wishlist:add', args=[self.product.pk])),
            ('POST', reverse('wishlist:remove', args=[self.product.pk])),
            ('GET', reverse('wishlist:status', args=[self.product.pk])),
            ('GET', reverse('wishlist:count')),
        ]
        for method, url in endpoints:
            with self.subTest(method=method, url=url):
                if method == 'POST':
                    response = self.client.post(url)
                else:
                    response = self.client.get(url)
                self.assertIn(
                    response.status_code, [401, 403, 302],
                    f'{method} {url} should reject anonymous',
                )
