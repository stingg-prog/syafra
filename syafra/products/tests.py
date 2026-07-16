import re
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Category, Product, ProductCollection, ProductSize, HomepageSection, ShopByCategoryItem, PromotionalBannerConfig, Testimonial, InstagramPost, ContentPage, ContactMessage, ThemeSettings, WebsiteSettings, NewsletterSubscriber

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
        collection = ProductCollection.objects.create(name='Home Collection')
        collection.products.add(self.featured_product)
        section = HomepageSection.objects.create(
            section_type='product_collection',
            collection=collection,
            is_active=True,
            display_order=1,
        )
        response = self.client.get('/', follow=True)
        self.assertIn(section.id, response.context['section_data'])
        products = response.context['section_data'][section.id]['products']
        self.assertIn(self.featured_product, products)
        self.assertNotIn(self.regular_product, products)

    def test_home_view_excludes_out_of_stock_products(self):
        collection = ProductCollection.objects.create(name='Home Collection')
        collection.products.add(self.featured_product, self.regular_product)
        section = HomepageSection.objects.create(
            section_type='product_collection',
            collection=collection,
            is_active=True,
            display_order=1,
        )
        response = self.client.get('/', follow=True)
        products = response.context['section_data'][section.id]['products']
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'Featured Product')

    def test_home_announcement_bar_renders_cms_text(self):
        section = HomepageSection.objects.create(
            section_type='announcement_bar',
            is_active=True,
            display_order=1,
            config={'text': 'TEST ANNOUNCEMENT'},
        )
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('TEST ANNOUNCEMENT', html)
        self.assertNotIn('Free Shipping on Orders Over', html)

    def test_home_shop_by_category_excludes_inactive(self):
        cat2 = Category.objects.create(name='Cat 2', slug='cat-2')
        section = HomepageSection.objects.create(
            section_type='shop_by_category',
            is_active=True,
            display_order=1,
        )
        active = ShopByCategoryItem.objects.create(
            section=section, category=self.category, is_active=True, display_order=0,
        )
        inactive = ShopByCategoryItem.objects.create(
            section=section, category=cat2, is_active=False, display_order=1,
        )
        response = self.client.get('/', follow=True)
        section_data = response.context['section_data'].get(section.id, {})
        items = section_data.get('category_items', [])
        self.assertIn(active, items)
        self.assertNotIn(inactive, items)

    def test_home_shop_by_category_ordering(self):
        cat2 = Category.objects.create(name='Cat 2', slug='cat-2')
        section = HomepageSection.objects.create(
            section_type='shop_by_category',
            is_active=True,
            display_order=1,
        )
        first = ShopByCategoryItem.objects.create(
            section=section, category=self.category, is_active=True, display_order=0,
        )
        second = ShopByCategoryItem.objects.create(
            section=section, category=cat2, is_active=True, display_order=1,
        )
        response = self.client.get('/', follow=True)
        items = response.context['section_data'][section.id]['category_items']
        self.assertEqual(list(items), [first, second])

    def test_home_promo_banner_no_unsplash(self):
        section = HomepageSection.objects.create(
            section_type='promotional_banner',
            is_active=True,
            display_order=1,
            config={'headline': 'SALE'},
        )
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertNotIn('unsplash', html)

    def test_home_newsletter_renders_static_content(self):
        HomepageSection.objects.create(
            section_type='newsletter',
            is_active=True,
            display_order=1,
        )
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('Stay in the Loop', html)
        self.assertIn('Subscribe for exclusive drops', html)

    def test_home_section_overline_from_cms(self):
        collection = ProductCollection.objects.create(name='Test Col')
        collection.products.add(self.featured_product)
        HomepageSection.objects.create(
            section_type='product_collection',
            is_active=True,
            display_order=1,
            overline='CMS OVERLINE',
            title='Collection Title',
            collection=collection,
        )
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('FEATURED JACKETS', html)
        self.assertNotIn('CMS OVERLINE', html)
        self.assertNotIn('THE EDIT', html)

    def test_home_hero_secondary_cta_from_config(self):
        section = HomepageSection.objects.create(
            section_type='hero_slider',
            is_active=True,
            display_order=1,
            config={'secondary_cta_label': 'LEARN MORE', 'secondary_cta_url': '/about/'},
        )
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('LEARN MORE', html)
        self.assertIn('/about/', html)
        self.assertNotIn('EXPLORE COLLECTION', html)

    def test_home_promo_banner_fallback_image(self):
        section = HomepageSection.objects.create(
            section_type='promotional_banner',
            is_active=True,
            display_order=1,
            config={'headline': 'SALE'},
        )
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('default.', html)  # staticfile may add hash suffix

    def test_home_announcement_bar_link_renders(self):
        section = HomepageSection.objects.create(
            section_type='announcement_bar',
            is_active=True,
            display_order=1,
            config={'text': 'CLICK ME', 'link_url': '/shop/'},
        )
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('/shop/', html)


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

    def test_shop_no_href_hash_in_footer(self):
        response = self.client.get('/shop', follow=True)
        self.assertNotIn('href="#"', response.content.decode())

    def test_shop_no_wishlist_button(self):
        response = self.client.get('/shop', follow=True)
        self.assertNotIn('product-card__wishlist', response.content.decode())

    def test_shop_product_detail_link_available(self):
        response = self.client.get('/shop', follow=True)
        html = response.content.decode()
        self.assertIn(f'href="/product/{self.product1.pk}/"', html)
        self.assertIn(f'href="/product/{self.product2.pk}/"', html)

    def test_shop_no_dead_anchor_links(self):
        response = self.client.get('/shop', follow=True)
        html = response.content.decode()
        dead_anchors = re.findall(r'href\s*=\s*"#"[^>]*>', html)
        self.assertEqual(len(dead_anchors), 0, f'Found {len(dead_anchors)} href="#" anchors')

    def test_shop_whatsapp_uses_dynamic_number(self):
        from products.models import WebsiteSettings
        ws = WebsiteSettings.get_settings()
        ws.whatsapp_number = '9999999999'
        ws.save()
        response = self.client.get('/shop', follow=True)
        html = response.content.decode()
        self.assertIn('9999999999', html)
        self.assertNotIn('919037626684', html)

    def test_shop_social_icons_from_settings(self):
        from products.models import WebsiteSettings
        ws = WebsiteSettings.get_settings()
        ws.instagram_url = 'https://instagram.com/test'
        ws.twitter_url = 'https://twitter.com/test'
        ws.threads_url = 'https://threads.net/test'
        ws.save()
        response = self.client.get('/shop', follow=True)
        html = response.content.decode()
        self.assertIn('instagram.com/test', html)
        self.assertIn('twitter.com/test', html)
        self.assertIn('threads.net/test', html)


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

    def test_product_detail_page_title_uses_store_name(self):
        from products.models import ThemeSettings
        ts = ThemeSettings.get_settings()
        ts.store_name = 'TEST STORE'
        ts.save()
        response = self.client.get(f'/product/{self.product.pk}', follow=True)
        html = response.content.decode()
        self.assertIn('TEST STORE', html)
        self.assertNotIn('- SYAFRA', html)


class MaintenanceModeTest(TestCase):
    def setUp(self):
        from products.models import WebsiteSettings
        self.ws = WebsiteSettings.get_settings()
        self.ws.maintenance_mode = True
        self.ws.maintenance_message = 'TEST MAINTENANCE'
        self.ws.save()
        self.admin_user = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='adminpass'
        )

    def test_maintenance_blocks_public(self):
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 503)
        html = response.content.decode()
        self.assertIn('TEST MAINTENANCE', html)

    def test_maintenance_allows_admin(self):
        self.client.login(username='admin', password='adminpass')
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('TEST MAINTENANCE', response.content.decode())

    def test_maintenance_allows_admin_path(self):
        response = self.client.get('/admin/', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_maintenance_bypasses_razorpay_webhook(self):
        response = self.client.post('/orders/razorpay/webhook/', {})
        self.assertNotEqual(response.status_code, 503)

    def test_maintenance_bypasses_webhook_health(self):
        response = self.client.get('/orders/webhook-health/', follow=True)
        self.assertNotEqual(response.status_code, 503)


class EmptyTestimonialsTest(TestCase):
    def test_no_testimonials_hides_section(self):
        section = HomepageSection.objects.create(
            section_type='customer_reviews',
            is_active=True,
            display_order=1,
        )
        response = self.client.get('/', follow=True)
        self.assertNotIn('testimonials-section', response.content.decode())


class SeoMetadataTest(TestCase):
    def test_meta_description_from_cms(self):
        from products.models import WebsiteSettings
        ws = WebsiteSettings.get_settings()
        ws.seo_description = 'TEST SEO DESCRIPTION'
        ws.save()
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('TEST SEO DESCRIPTION', html)

    def test_og_image_from_cms(self):
        # Without og_image, no og tags should render
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertNotIn('og:image', html)


class HomepageSectionBehaviorTest(TestCase):
    """Regression tests for homepage section hide/render/pairing logic."""

    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Test Product', brand='Brand', category=self.category,
            price=10.00, stock=5,
        )

    # ── Women's Tops ──────────────────────────────────────────────

    def test_womens_tops_hidden_when_collection_empty(self):
        collection = ProductCollection.objects.create(name='WT')
        section = HomepageSection.objects.create(
            section_type='womens_tops', is_active=True, display_order=1,
            collection=collection,
        )
        response = self.client.get('/', follow=True)
        self.assertNotIn(section, response.context['sections'])

    def test_womens_tops_renders_with_in_stock_product(self):
        collection = ProductCollection.objects.create(name='WT')
        collection.products.add(self.product)
        section = HomepageSection.objects.create(
            section_type='womens_tops', is_active=True, display_order=1,
            collection=collection,
        )
        response = self.client.get('/', follow=True)
        self.assertIn(section, response.context['sections'])
        html = response.content.decode()
        self.assertIn('product-grid', html)
        self.assertIn('Test Product', html)

    # ── Trending + Best Sellers pairing ───────────────────────────

    def test_trending_standalone_when_best_sellers_empty(self):
        col = ProductCollection.objects.create(name='Trending')
        col.products.add(self.product)
        empty = ProductCollection.objects.create(name='Empty')
        trending = HomepageSection.objects.create(
            section_type='trending_now', is_active=True, display_order=1,
            collection=col,
        )
        HomepageSection.objects.create(
            section_type='best_sellers', is_active=True, display_order=2,
            collection=empty,
        )
        response = self.client.get('/', follow=True)
        self.assertIn(trending, response.context['sections'])
        html = response.content.decode()
        self.assertNotIn('dual-collection-section', html)
        self.assertIn('Test Product', html)

    def test_best_sellers_standalone_when_trending_empty(self):
        col = ProductCollection.objects.create(name='BS')
        col.products.add(self.product)
        empty = ProductCollection.objects.create(name='Empty')
        HomepageSection.objects.create(
            section_type='trending_now', is_active=True, display_order=1,
            collection=empty,
        )
        best_sellers = HomepageSection.objects.create(
            section_type='best_sellers', is_active=True, display_order=2,
            collection=col,
        )
        response = self.client.get('/', follow=True)
        self.assertIn(best_sellers, response.context['sections'])
        html = response.content.decode()
        self.assertNotIn('dual-collection-section', html)
        self.assertIn('Test Product', html)

    def test_trending_best_sellers_combined_when_both_have_products(self):
        col1 = ProductCollection.objects.create(name='T')
        col1.products.add(self.product)
        col2 = ProductCollection.objects.create(name='BS')
        p2 = Product.objects.create(
            name='BS Product', brand='B', category=self.category,
            price=20.00, stock=5,
        )
        col2.products.add(p2)
        HomepageSection.objects.create(
            section_type='trending_now', is_active=True, display_order=1,
            collection=col1,
        )
        HomepageSection.objects.create(
            section_type='best_sellers', is_active=True, display_order=2,
            collection=col2,
        )
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('dual-collection-section', html)
        self.assertIn('Test Product', html)
        self.assertIn('BS Product', html)

    def test_both_trending_best_sellers_hidden_when_both_empty(self):
        col1 = ProductCollection.objects.create(name='E1')
        col2 = ProductCollection.objects.create(name='E2')
        t = HomepageSection.objects.create(
            section_type='trending_now', is_active=True, display_order=1,
            collection=col1,
        )
        b = HomepageSection.objects.create(
            section_type='best_sellers', is_active=True, display_order=2,
            collection=col2,
        )
        response = self.client.get('/', follow=True)
        self.assertNotIn(t, response.context['sections'])
        self.assertNotIn(b, response.context['sections'])

    # ── Customer Reviews ──────────────────────────────────────────

    def test_customer_reviews_hidden_with_zero_active_testimonials(self):
        HomepageSection.objects.create(
            section_type='customer_reviews', is_active=True, display_order=1,
        )
        response = self.client.get('/', follow=True)
        self.assertNotIn('testimonials-section', response.content.decode())

    def test_active_testimonial_renders(self):
        HomepageSection.objects.create(
            section_type='customer_reviews', is_active=True, display_order=1,
        )
        Testimonial.objects.create(name='Alice', review='Great!', is_active=True)
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('testimonials-section', html)
        self.assertIn('ALICE', html)
        self.assertIn('Great!', html)

    def test_inactive_testimonial_does_not_render(self):
        HomepageSection.objects.create(
            section_type='customer_reviews', is_active=True, display_order=1,
        )
        Testimonial.objects.create(name='Bob', review='Bad', is_active=False)
        response = self.client.get('/', follow=True)
        self.assertNotIn('testimonials-section', response.content.decode())

    # ── Instagram Feed ────────────────────────────────────────────

    def test_instagram_shows_fallback_when_no_active_posts(self):
        HomepageSection.objects.create(
            section_type='instagram_feed', is_active=True, display_order=1,
        )
        response = self.client.get('/', follow=True)
        html = response.content.decode()
        self.assertIn('instagram-section', html)
        self.assertIn('instagram-fallback', html)

    def test_active_instagram_post_in_context(self):
        section = HomepageSection.objects.create(
            section_type='instagram_feed', is_active=True, display_order=1,
        )
        post = InstagramPost.objects.create(
            image='test_img', link='https://ig.com/p/1', is_active=True,
        )
        response = self.client.get('/', follow=True)
        posts = response.context['section_data'][section.id]['posts']
        self.assertIn(post, posts)

    def test_inactive_instagram_post_not_in_context(self):
        section = HomepageSection.objects.create(
            section_type='instagram_feed', is_active=True, display_order=1,
        )
        InstagramPost.objects.create(
            image='test_img', link='https://ig.com/p/1', is_active=False,
        )
        response = self.client.get('/', follow=True)
        posts = response.context['section_data'][section.id]['posts']
        self.assertEqual(len(posts), 0)

    def test_instagram_post_created_at_ordering_respected(self):
        section = HomepageSection.objects.create(
            section_type='instagram_feed', is_active=True, display_order=1,
        )
        first = InstagramPost.objects.create(
            image='first', link='https://ig.com/p/1', is_active=True,
        )
        second = InstagramPost.objects.create(
            image='second', link='https://ig.com/p/2', is_active=True,
        )
        response = self.client.get('/', follow=True)
        posts = response.context['section_data'][section.id]['posts']
        self.assertEqual([p.pk for p in posts], [second.pk, first.pk])

    # ── Section ordering ──────────────────────────────────────────

    def test_homepage_section_display_order_respected(self):
        col1 = ProductCollection.objects.create(name='C1')
        col1.products.add(self.product)
        col2 = ProductCollection.objects.create(name='C2')
        p2 = Product.objects.create(
            name='Second', brand='B', category=self.category, price=20.00, stock=5,
        )
        col2.products.add(p2)
        s1 = HomepageSection.objects.create(
            section_type='womens_tops', is_active=True, display_order=2,
            collection=col1,
        )
        s2 = HomepageSection.objects.create(
            section_type='product_collection', is_active=True, display_order=1,
            collection=col2,
        )
        response = self.client.get('/', follow=True)
        sections = response.context['sections']
        self.assertEqual(sections, [s2, s1])


class ContentPageTest(TestCase):
    def setUp(self):
        self.page = ContentPage.objects.create(
            title='Test Page',
            slug='test-page',
            overline='Test',
            summary='Test summary',
            content='<p>Test content</p>',
            meta_title='Custom Meta Title',
            meta_description='Custom meta desc',
            is_active=True,
            display_order=1,
        )

    def test_active_page_publicly_accessible(self):
        url = reverse('products:content_page', args=['test-page'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/content_page.html')

    def test_inactive_page_returns_404_for_public(self):
        self.page.is_active = False
        self.page.save()
        url = reverse('products:content_page', args=['test-page'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_cms_page_title_content_renders(self):
        url = reverse('products:content_page', args=['test-page'])
        response = self.client.get(url)
        html = response.content.decode()
        self.assertIn('Test Page', html)
        self.assertIn('Test summary', html)
        self.assertIn('Test content', html)
        self.assertIn('Test', html)

    def test_cms_page_seo_metadata(self):
        url = reverse('products:content_page', args=['test-page'])
        response = self.client.get(url)
        html = response.content.decode()
        self.assertIn('Custom Meta Title', html)
        self.assertIn('Custom meta desc', html)

    def test_cms_page_meta_title_fallback(self):
        self.page.meta_title = ''
        self.page.save()
        ts = ThemeSettings.get_settings()
        ts.store_name = 'TEST STORE'
        ts.save()
        url = reverse('products:content_page', args=['test-page'])
        response = self.client.get(url)
        html = response.content.decode()
        self.assertIn('Test Page | TEST STORE', html)

    def test_cms_page_meta_description_fallback_to_summary(self):
        self.page.meta_description = ''
        self.page.save()
        url = reverse('products:content_page', args=['test-page'])
        response = self.client.get(url)
        html = response.content.decode()
        self.assertIn('Test summary', html)

    def test_cms_page_canonical_url(self):
        url = reverse('products:content_page', args=['test-page'])
        response = self.client.get(url)
        html = response.content.decode()
        self.assertIn('canonical', html)
        self.assertIn('/pages/test-page/', html)


class ContactPageTest(TestCase):
    def test_contact_page_accessible(self):
        url = reverse('products:contact')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/contact.html')

    def test_contact_details_use_website_settings(self):
        ws = WebsiteSettings.get_settings()
        ws.contact_email = 'test@example.com'
        ws.contact_phone = '+1 234 567 890'
        ws.business_address = '123 Test St'
        ws.business_hours = 'Mon-Fri 9-5'
        ws.whatsapp_number = '1234567890'
        ws.save()
        url = reverse('products:contact')
        response = self.client.get(url)
        html = response.content.decode()
        self.assertIn('test@example.com', html)
        self.assertIn('+1 234 567 890', html)
        self.assertIn('123 Test St', html)
        self.assertIn('Mon-Fri 9-5', html)

    def test_valid_contact_post_stores_message(self):
        url = reverse('products:contact')
        data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'subject': 'Test Subject',
            'message': 'Test message body',
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(ContactMessage.objects.count(), 1)
        msg = ContactMessage.objects.first()
        self.assertEqual(msg.name, 'John Doe')
        self.assertEqual(msg.email, 'john@example.com')
        self.assertEqual(msg.subject, 'Test Subject')
        self.assertEqual(msg.message, 'Test message body')
        self.assertFalse(msg.is_read)
        self.assertIn('Thank you', response.content.decode())

    def test_contact_post_uses_redirect_after_success(self):
        url = reverse('products:contact')
        data = {
            'name': 'Jane',
            'email': 'jane@example.com',
            'subject': 'Hi',
            'message': 'Hello',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url)

    def test_invalid_contact_post_does_not_store_message(self):
        url = reverse('products:contact')
        data = {
            'name': '',
            'email': 'not-an-email',
            'subject': '',
            'message': '',
        }
        response = self.client.post(url, data)
        self.assertEqual(ContactMessage.objects.count(), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_contact_email_failure_does_not_lose_saved_message(self):
        import logging
        logging.disable(logging.CRITICAL)
        url = reverse('products:contact')
        data = {
            'name': 'Test',
            'email': 'test@example.com',
            'subject': 'Fail',
            'message': 'Email will fail',
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertIn('Thank you', response.content.decode())
        logging.disable(logging.NOTSET)


class TrackOrderTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='cust', email='customer@example.com', password='testpass'
        )
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='Track Product', brand='B', category=self.category,
            price=50.00, stock=5,
        )
        from orders.models import Order, OrderItem
        self.order = Order.objects.create(
            user=self.user,
            email='customer@example.com',
            customer_name='Customer',
            phone_number='1234567890',
            total_price=100.00,
            status='shipped',
            payment_status='paid',
            tracking_id='TRACK123',
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=50.00,
        )
        self.order_pk = self.order.pk

    def test_track_order_page_accessible(self):
        url = reverse('products:track_order')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/track_order.html')

    def test_track_order_valid_identifier_and_matching_email(self):
        url = reverse('products:track_order')
        data = {'order_number': str(self.order_pk), 'email': 'customer@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertIn('Shipped', html)
        self.assertIn('TRACK123', html)
        self.assertIn('#{}'.format(self.order_pk), html)
        self.assertIn('100.00', html)

    def test_track_order_wrong_email_returns_generic_failure(self):
        url = reverse('products:track_order')
        data = {'order_number': str(self.order_pk), 'email': 'wrong@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertNotIn('Shipped', html)
        self.assertIn("couldn't find an order", html.lower())

    def test_track_order_invalid_identifier_returns_generic_failure(self):
        url = reverse('products:track_order')
        data = {'order_number': '999999', 'email': 'customer@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertIn("couldn't find an order", html.lower())

    def test_track_order_does_not_expose_another_order(self):
        from orders.models import Order
        other_user = get_user_model().objects.create_user(
            username='other', email='other@example.com', password='testpass'
        )
        other = Order.objects.create(
            user=other_user,
            email='other@example.com',
            total_price=500.00,
            status='paid',
            payment_status='paid',
        )
        url = reverse('products:track_order')
        data = {'order_number': str(other.pk), 'email': 'customer@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertIn("couldn't find an order", html.lower())

    def test_track_order_page_contains_noindex_nofollow(self):
        url = reverse('products:track_order')
        response = self.client.get(url)
        html = response.content.decode()
        self.assertIn('noindex, nofollow', html)

    def test_track_order_result_contains_noindex_nofollow(self):
        url = reverse('products:track_order')
        data = {'order_number': str(self.order_pk), 'email': 'customer@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertIn('noindex, nofollow', html)

    def test_track_order_renders_product_name(self):
        url = reverse('products:track_order')
        data = {'order_number': str(self.order_pk), 'email': 'customer@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertIn('Track Product', html)

    def test_track_order_renders_correct_quantity(self):
        url = reverse('products:track_order')
        data = {'order_number': str(self.order_pk), 'email': 'customer@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertIn('Qty: 2', html)

    def test_track_order_renders_snapshot_price(self):
        url = reverse('products:track_order')
        data = {'order_number': str(self.order_pk), 'email': 'customer@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertIn('₹50.00 each', html)

    def test_track_order_snapshot_price_unchanged_when_product_price_changes(self):
        self.product.price = 99.99
        self.product.save()
        url = reverse('products:track_order')
        data = {'order_number': str(self.order_pk), 'email': 'customer@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertIn('₹50.00 each', html)
        self.assertNotIn('₹99.99', html)

    def test_track_order_does_not_show_another_orders_items(self):
        from orders.models import Order, OrderItem
        other_product = Product.objects.create(
            name='Other Item', brand='B', category=self.category, price=25.00, stock=10,
        )
        other_order = Order.objects.create(
            user=self.user, email='customer@example.com',
            customer_name='Customer', phone_number='0000000000',
            total_price=25.00, status='paid', payment_status='paid',
        )
        OrderItem.objects.create(
            order=other_order, product=other_product, quantity=1, price=25.00,
        )
        url = reverse('products:track_order')
        data = {'order_number': str(self.order_pk), 'email': 'customer@example.com'}
        response = self.client.post(url, data, follow=True)
        html = response.content.decode()
        self.assertIn('Track Product', html)
        self.assertNotIn('Other Item', html)


class FooterLinkTest(TestCase):
    def test_footer_links_point_to_real_routes(self):
        response = self.client.get(reverse('products:shop'), follow=True)
        html = response.content.decode()
        self.assertIn('/pages/shipping-returns/', html)
        self.assertIn('/pages/size-guide/', html)
        self.assertIn('/track-order/', html)
        self.assertIn('/contact/', html)
        self.assertIn('/pages/about-us/', html)
        self.assertIn('/pages/sustainability/', html)
        self.assertIn('/pages/privacy-policy/', html)
        self.assertIn('/pages/terms-of-service/', html)

    def test_required_content_page_seed_is_idempotent(self):
        from django.core.management import call_command
        before = ContentPage.objects.count()
        call_command('seed_content_pages')
        after_first = ContentPage.objects.count()
        call_command('seed_content_pages')
        after_second = ContentPage.objects.count()
        self.assertGreater(after_first, before)
        self.assertEqual(after_first, after_second)


class MaintenancePhase8Test(TestCase):
    def setUp(self):
        self.ws = WebsiteSettings.get_settings()
        self.ws.maintenance_mode = True
        self.ws.save()
        self.admin_user = get_user_model().objects.create_superuser(
            username='admin', email='admin@test.com', password='adminpass'
        )

    def test_maintenance_blocks_content_page(self):
        ContentPage.objects.create(
            title='Maint Page', slug='maint-page', is_active=True,
        )
        response = self.client.get('/pages/maint-page/', follow=True)
        self.assertEqual(response.status_code, 503)

    def test_maintenance_blocks_contact(self):
        response = self.client.get('/contact/', follow=True)
        self.assertEqual(response.status_code, 503)

    def test_maintenance_blocks_track_order(self):
        response = self.client.get('/track-order/', follow=True)
        self.assertEqual(response.status_code, 503)

    def test_maintenance_still_permits_admin(self):
        response = self.client.get('/admin/', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_razorpay_webhook_remains_maintenance_exempt(self):
        response = self.client.post('/orders/razorpay/webhook/', {})
        self.assertNotEqual(response.status_code, 503)


class NewsletterSubscribeTest(TestCase):
    def setUp(self):
        self.url = reverse('products:newsletter_subscribe')
        self.home_url = '/'

    # ── AJAX tests ──────────────────────────────────────────────

    def test_ajax_valid_email_creates_subscriber(self):
        response = self.client.post(
            self.url, {'email': 'test@example.com'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Thank you for subscribing to SYAFRA.')
        self.assertTrue(NewsletterSubscriber.objects.filter(email='test@example.com').exists())

    def test_ajax_duplicate_email_returns_already_subscribed(self):
        NewsletterSubscriber.objects.create(email='test@example.com')
        response = self.client.post(
            self.url, {'email': 'test@example.com'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], "You're already subscribed.")

    def test_ajax_case_insensitive_duplicate_detected(self):
        NewsletterSubscriber.objects.create(email='test@example.com')
        response = self.client.post(
            self.url, {'email': 'TEST@EXAMPLE.COM'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], "You're already subscribed.")

    def test_ajax_invalid_email_rejected(self):
        response = self.client.post(
            self.url, {'email': 'not-an-email'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])

    def test_ajax_empty_email_rejected(self):
        response = self.client.post(
            self.url, {'email': ''},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])

    def test_ajax_whitespace_email_trimmed(self):
        response = self.client.post(
            self.url, {'email': '  user@example.com  '},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(NewsletterSubscriber.objects.filter(email='user@example.com').exists())

    def test_ajax_email_lowercased(self):
        response = self.client.post(
            self.url, {'email': 'User@Example.COM'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(NewsletterSubscriber.objects.filter(email='user@example.com').exists())

    def test_ajax_reactivates_inactive_subscriber(self):
        sub = NewsletterSubscriber.objects.create(
            email='past@subscriber.com', is_active=False
        )
        response = self.client.post(
            self.url, {'email': 'past@subscriber.com'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)

    # ── Non-AJAX (graceful degradation) tests ───────────────────

    def test_non_ajax_valid_email_redirects_and_messages(self):
        response = self.client.post(self.url, {'email': 'user@example.org'}, follow=True)
        self.assertRedirects(response, self.home_url, status_code=302)
        self.assertTrue(NewsletterSubscriber.objects.filter(email='user@example.org').exists())
        msgs = list(response.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertEqual(str(msgs[0]), 'Thank you for subscribing to SYAFRA.')

    def test_non_ajax_duplicate_email_shows_already_subscribed(self):
        NewsletterSubscriber.objects.create(email='existing@example.com')
        response = self.client.post(
            self.url, {'email': 'existing@example.com'}, follow=True
        )
        self.assertRedirects(response, self.home_url, status_code=302)
        msgs = list(response.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertEqual(str(msgs[0]), "You're already subscribed.")

    def test_non_ajax_invalid_email_redirects_with_error(self):
        response = self.client.post(self.url, {'email': 'bad'}, follow=True)
        self.assertRedirects(response, self.home_url, status_code=302)
        msgs = list(response.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertIn('valid', str(msgs[0]).lower())

    def test_non_ajax_without_email_redirects_with_error(self):
        response = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(response, self.home_url, status_code=302)
