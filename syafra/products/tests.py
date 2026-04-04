from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Category, Product, ProductSize

User = get_user_model()


class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics',
            description='Electronic devices'
        )
        self.product = Product.objects.create(
            name='Test Product',
            brand='Test Brand',
            category=self.category,
            condition='new',
            price=99.99,
            description='A test product',
            stock=10,
            is_featured=True
        )
        ProductSize.objects.create(product=self.product, size='M', stock=5)
        ProductSize.objects.create(product=self.product, size='L', stock=3)

    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.brand, 'Test Brand')
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.product.price, 99.99)
        self.assertEqual(self.product.stock, 10)
        self.assertTrue(self.product.is_featured)

    def test_product_str(self):
        self.assertEqual(str(self.product), 'Test Product')

    def test_product_absolute_url(self):
        url = self.product.get_absolute_url()
        self.assertEqual(url, f'/product/{self.product.pk}/')

    def test_product_get_available_sizes(self):
        sizes = self.product.get_available_sizes()
        self.assertEqual(sizes, ['M', 'L'])


class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Clothing',
            slug='clothing',
            description='Apparel items'
        )

    def test_category_creation(self):
        self.assertEqual(self.category.name, 'Clothing')
        self.assertEqual(self.category.slug, 'clothing')

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Clothing')


class HomeViewTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.featured_product = Product.objects.create(
            name='Featured Product',
            brand='Test Brand',
            category=self.category,
            price=100.00,
            stock=5,
            is_featured=True
        )
        self.regular_product = Product.objects.create(
            name='Regular Product',
            brand='Test Brand',
            category=self.category,
            price=50.00,
            stock=0,
            is_featured=False
        )

    def test_home_view_status_code(self):
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_home_view_uses_correct_template(self):
        response = self.client.get('/', follow=True)
        self.assertTemplateUsed(response, 'home.html')

    def test_home_view_shows_featured_products(self):
        response = self.client.get('/', follow=True)
        self.assertIn('featured_products', response.context)
        self.assertEqual(list(response.context['featured_products']), [self.featured_product])

    def test_home_view_excludes_out_of_stock_products(self):
        response = self.client.get('/', follow=True)
        featured = response.context['featured_products']
        self.assertEqual(len(featured), 1)
        self.assertEqual(featured[0].name, 'Featured Product')


class ShopViewTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.product1 = Product.objects.create(
            name='Product 1',
            brand='Brand A',
            category=self.category,
            price=100.00,
            stock=5
        )
        ProductSize.objects.create(product=self.product1, size='M', stock=3)
        self.product2 = Product.objects.create(
            name='Product 2',
            brand='Brand B',
            category=self.category,
            price=50.00,
            stock=0
        )

    def test_shop_view_status_code(self):
        response = self.client.get('/shop', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_shop_view_uses_correct_template(self):
        response = self.client.get('/shop', follow=True)
        self.assertTemplateUsed(response, 'shop.html')

    def test_shop_view_shows_all_products(self):
        response = self.client.get('/shop', follow=True)
        self.assertIn('products', response.context)
        products = list(response.context['products'])
        self.assertEqual(len(products), 2)
        self.assertIn(self.product1, products)
        self.assertIn(self.product2, products)

    def test_shop_view_search(self):
        response = self.client.get('/shop?search=Product 1', follow=True)
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'Product 1')

    def test_shop_view_filter_category(self):
        response = self.client.get('/shop?category=test-category', follow=True)
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 2)

    def test_shop_view_filter_size(self):
        response = self.client.get('/shop?size=M', follow=True)
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'Product 1')

    def test_shop_view_filter_in_stock(self):
        response = self.client.get('/shop?stock=in_stock', follow=True)
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'Product 1')

    def test_shop_view_filter_sold_out(self):
        response = self.client.get('/shop?stock=sold_out', follow=True)
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'Product 2')

    def test_shop_view_pagination(self):
        for i in range(15):
            Product.objects.create(
                name=f'Product {i}',
                brand='Brand',
                category=self.category,
                price=100.00,
                stock=5
            )
        
        response = self.client.get('/shop', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(response.context['products'], 'paginator'))
        self.assertEqual(response.context['products'].paginator.per_page, 12)


class ProductDetailViewTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.product = Product.objects.create(
            name='Test Product',
            brand='Test Brand',
            category=self.category,
            condition='new',
            price=199.99,
            description='A detailed description',
            stock=10,
            is_featured=True
        )
        ProductSize.objects.create(product=self.product, size='L', stock=5)
        self.related_product = Product.objects.create(
            name='Related Product',
            brand='Test Brand',
            category=self.category,
            price=99.99,
            stock=5
        )

    def test_product_detail_view_status_code(self):
        response = self.client.get(f'/product/{self.product.pk}', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_product_detail_view_uses_correct_template(self):
        response = self.client.get(f'/product/{self.product.pk}', follow=True)
        self.assertTemplateUsed(response, 'product_detail.html')

    def test_product_detail_view_returns_product(self):
        response = self.client.get(f'/product/{self.product.pk}', follow=True)
        self.assertIn('product', response.context)
        self.assertEqual(response.context['product'], self.product)

    def test_product_detail_view_returns_related_products(self):
        response = self.client.get(f'/product/{self.product.pk}', follow=True)
        self.assertIn('related_products', response.context)
        related = list(response.context['related_products'])
        self.assertEqual(related, [self.related_product])

    def test_product_detail_view_404_for_nonexistent_product(self):
        response = self.client.get('/product/9999', follow=True)
        self.assertEqual(response.status_code, 404)
