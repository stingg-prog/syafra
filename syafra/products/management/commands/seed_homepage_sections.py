from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import (
    HomepageSection, HeroSlide, TrustBarItem, ShopByCategoryItem,
    FooterLink, ProductCollection, Category, ThemeSettings, WebsiteSettings
)


class Command(BaseCommand):
    help = 'Seeds initial homepage sections, theme settings, and website settings'

    def handle(self, *args, **options):
        self.stdout.write('Seeding homepage sections...')

        # Create ThemeSettings (singleton)
        theme, _ = ThemeSettings.objects.get_or_create(pk=1, defaults={
            'store_name': 'SYAFRA',
            'tagline': 'Fashion-Forward Vintage Streetwear',
            'primary_color': '#000000',
            'secondary_color': '#FFFFFF',
            'accent_color': '#E8DCC4',
        })
        self.stdout.write(self.style.SUCCESS('Theme Settings created'))

        # Create WebsiteSettings (singleton)
        website, _ = WebsiteSettings.objects.get_or_create(pk=1, defaults={
            'contact_email': 'hello@syafra.com',
            'contact_phone': '+91 90376 26684',
            'business_address': '',
            'business_hours': 'Mon-Sat: 10AM - 8PM',
            'whatsapp_number': '919037626684',
            'whatsapp_default_message': 'Hi, I am interested in your products. Please share more details.',
            'seo_title': 'SYAFRA - Fashion-Forward Vintage Streetwear',
            'seo_description': 'Curated vintage jackets and streetwear. Authentic pieces, modern style.',
            'seo_keywords': 'vintage jackets, streetwear, fashion, thrift',
            'copyright_text': '2026 SYAFRA. All rights reserved.',
            'instagram_url': 'https://www.instagram.com/syafra.thrift/',
        })
        self.stdout.write(self.style.SUCCESS('Website Settings created'))

        # Section 1: Announcement Bar
        announcement, created = HomepageSection.objects.get_or_create(
            section_type='announcement_bar',
            defaults={
                'title': 'FREE SHIPPING ON ORDERS OVER ₹5000',
                'display_order': 1,
                'is_active': True,
                'config': {
                    'text': 'FREE SHIPPING ON ORDERS OVER ₹5000',
                    'bg_color': '#000000',
                    'text_color': '#FFFFFF',
                },
            }
        )
        if created:
            self.stdout.write('Created: Announcement Bar')

        # Section 2: Hero Slider
        hero_section, created = HomepageSection.objects.get_or_create(
            section_type='hero_slider',
            defaults={
                'title': 'Hero Slider',
                'display_order': 2,
                'is_active': True,
                'config': {
                    'auto_play': True,
                    'interval': 5000,
                    'show_dots': True,
                    'show_arrows': True,
                },
            }
        )
        if created:
            # Create default hero slides
            slides_data = [
                {
                    'title': 'VINTAGE COLLECTION',
                    'subtitle': 'NEW ARRIVALS',
                    'description': 'Discover curated vintage jackets with modern style',
                    'button_text': 'SHOP NOW',
                    'button_url': '/shop/',
                    'overlay_opacity': 60,
                },
                {
                    'title': 'PREMIUM LEATHER',
                    'subtitle': 'HANDSELECTED',
                    'description': 'Authentic leather jackets from iconic brands',
                    'button_text': 'EXPLORE',
                    'button_url': '/shop/?category=leather-jackets',
                    'overlay_opacity': 60,
                },
            ]
            for i, slide_data in enumerate(slides_data):
                HeroSlide.objects.get_or_create(
                    section=hero_section,
                    display_order=i,
                    defaults=slide_data
                )
            self.stdout.write('Created: Hero Slider with 2 slides')

        # Section 3: Trust Bar
        trust_section, created = HomepageSection.objects.get_or_create(
            section_type='trust_bar',
            defaults={
                'title': 'Trust Bar',
                'display_order': 3,
                'is_active': True,
            }
        )
        if created:
            trust_items = [
                {
                    'icon_svg': 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
                    'title': 'Free Shipping',
                    'description': 'On orders over ₹5000',
                },
                {
                    'icon_svg': 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
                    'title': 'Authenticity Guaranteed',
                    'description': '100% genuine products',
                },
                {
                    'icon_svg': 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
                    'title': 'Easy Returns',
                    'description': '7-day return policy',
                },
                {
                    'icon_svg': 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
                    'title': 'Secure Payment',
                    'description': '100% secure checkout',
                },
            ]
            for i, item_data in enumerate(trust_items):
                TrustBarItem.objects.get_or_create(
                    section=trust_section,
                    title=item_data['title'],
                    defaults={**item_data, 'display_order': i}
                )
            self.stdout.write('Created: Trust Bar with 4 items')

        # Section 4: Shop By Category
        category_section, created = HomepageSection.objects.get_or_create(
            section_type='shop_by_category',
            defaults={
                'title': 'Shop by Category',
                'subtitle': 'Find Your Perfect Style',
                'display_order': 4,
                'is_active': True,
            }
        )
        if created:
            # Link existing categories
            categories = Category.objects.all()[:6]
            for i, cat in enumerate(categories):
                ShopByCategoryItem.objects.get_or_create(
                    section=category_section,
                    category=cat,
                    defaults={
                        'headline': cat.name.upper(),
                        'label': 'EXPLORE',
                        'display_order': i,
                    }
                )
            self.stdout.write(f'Created: Shop By Category with {categories.count()} items')

        # Section 5: Featured Jackets (Product Collection)
        featured_collection, _ = ProductCollection.objects.get_or_create(
            name='Featured Jackets',
            defaults={
                'description': 'Handpicked premium vintage jackets',
            }
        )
        featured_section, created = HomepageSection.objects.get_or_create(
            section_type='product_collection',
            defaults={
                'title': 'Featured Jackets',
                'subtitle': 'Handpicked Premium Vintage',
                'collection': featured_collection,
                'display_order': 5,
                'is_active': True,
                'config': {
                    'max_items': 12,
                    'show_view_all': True,
                    'view_all_url': '/shop/',
                },
            }
        )
        if created:
            self.stdout.write('Created: Featured Jackets collection section')

        # Section 5b: Women's Tops (Product Collection)
        womens_collection, _ = ProductCollection.objects.get_or_create(
            name="Women's Tops",
            defaults={
                'description': "Curated women's vintage tops and blouses",
            }
        )
        womens_section, created = HomepageSection.objects.get_or_create(
            section_type='womens_tops',
            defaults={
                'title': "Women's Tops",
                'subtitle': 'Vintage Elegance Redefined',
                'collection': womens_collection,
                'display_order': 6,
                'is_active': True,
                'config': {
                    'max_items': 12,
                    'show_view_all': True,
                    'view_all_url': '/shop/',
                },
            }
        )
        if created:
            self.stdout.write("Created: Women's Tops collection section")

        # Section 5c: Trending Now (Product Collection)
        trending_collection, _ = ProductCollection.objects.get_or_create(
            name='Trending Now',
            defaults={
                'description': 'Currently trending vintage pieces',
            }
        )
        trending_section, created = HomepageSection.objects.get_or_create(
            section_type='trending_now',
            defaults={
                'title': 'Trending Now',
                'subtitle': 'What Everyone Is Wearing',
                'collection': trending_collection,
                'display_order': 7,
                'is_active': True,
                'config': {
                    'max_items': 12,
                    'show_view_all': True,
                    'view_all_url': '/shop/',
                },
            }
        )
        if created:
            self.stdout.write('Created: Trending Now collection section')

        # Section 5d: Best Sellers (Product Collection)
        bestsellers_collection, _ = ProductCollection.objects.get_or_create(
            name='Best Sellers',
            defaults={
                'description': 'Most popular vintage pieces',
            }
        )
        bestsellers_section, created = HomepageSection.objects.get_or_create(
            section_type='best_sellers',
            defaults={
                'title': 'Best Sellers',
                'subtitle': 'Customer Favorites',
                'collection': bestsellers_collection,
                'display_order': 8,
                'is_active': True,
                'config': {
                    'max_items': 12,
                    'show_view_all': True,
                    'view_all_url': '/shop/',
                },
            }
        )
        if created:
            self.stdout.write('Created: Best Sellers collection section')

        # Shift existing sections to make room for new ones
        order_shifts = {
            'promotional_banner': 9,
            'customer_reviews': 10,
            'instagram_feed': 11,
            'newsletter': 12,
            'footer': 13,
        }
        for stype, new_order in order_shifts.items():
            HomepageSection.objects.filter(section_type=stype).exclude(
                display_order=new_order
            ).update(display_order=new_order)

        # Section 6: Promotional Banner
        promo_section, created = HomepageSection.objects.get_or_create(
            section_type='promotional_banner',
            defaults={
                'title': 'Season Sale',
                'subtitle': 'UP TO 40% OFF',
                'display_order': 6,
                'is_active': True,
                'config': {
                    'bg_color': '#1a1a1a',
                    'text_color': '#FFFFFF',
                    'button_text': 'SHOP SALE',
                    'button_url': '/shop/',
                },
            }
        )
        if created:
            self.stdout.write('Created: Promotional Banner')

        # Section 7: Customer Reviews
        reviews_section, created = HomepageSection.objects.get_or_create(
            section_type='customer_reviews',
            defaults={
                'title': 'What Our Customers Say',
                'subtitle': 'Trusted by Fashion Enthusiasts',
                'display_order': 7,
                'is_active': True,
                'config': {
                    'max_items': 3,
                },
            }
        )
        if created:
            self.stdout.write('Created: Customer Reviews section')

        # Section 8: Instagram Feed
        instagram_section, created = HomepageSection.objects.get_or_create(
            section_type='instagram_feed',
            defaults={
                'title': '@syafra.thrift',
                'subtitle': 'Follow Us on Instagram',
                'display_order': 8,
                'is_active': True,
                'config': {
                    'max_items': 6,
                },
            }
        )
        if created:
            self.stdout.write('Created: Instagram Feed section')

        # Section 9: Newsletter
        newsletter_section, created = HomepageSection.objects.get_or_create(
            section_type='newsletter',
            defaults={
                'title': 'Stay in the Loop',
                'subtitle': 'Subscribe for exclusive offers and new arrivals',
                'display_order': 9,
                'is_active': True,
                'config': {
                    'placeholder': 'Enter your email',
                    'button_text': 'SUBSCRIBE',
                },
            }
        )
        if created:
            self.stdout.write('Created: Newsletter section')

        # Section 10: Footer
        footer_section, created = HomepageSection.objects.get_or_create(
            section_type='footer',
            defaults={
                'title': 'Footer',
                'display_order': 10,
                'is_active': True,
            }
        )
        if created:
            footer_links = [
                {'column_heading': 'SHOP', 'label': 'All Products', 'url': '/shop/', 'display_order': 1},
                {'column_heading': 'SHOP', 'label': 'Leather Jackets', 'url': '/shop/?category=leather-jackets', 'display_order': 2},
                {'column_heading': 'SHOP', 'label': 'Denim Jackets', 'url': '/shop/?category=denim-jackets', 'display_order': 3},
                {'column_heading': 'SHOP', 'label': 'Bomber Jackets', 'url': '/shop/?category=bomber-jackets', 'display_order': 4},
                {'column_heading': 'HELP', 'label': 'Contact Us', 'url': '/contact/', 'display_order': 5},
                {'column_heading': 'HELP', 'label': 'Shipping Info', 'url': '/shipping/', 'display_order': 6},
                {'column_heading': 'HELP', 'label': 'Returns', 'url': '/returns/', 'display_order': 7},
                {'column_heading': 'HELP', 'label': 'FAQ', 'url': '/faq/', 'display_order': 8},
            ]
            for link_data in footer_links:
                FooterLink.objects.get_or_create(
                    section=footer_section,
                    label=link_data['label'],
                    defaults=link_data
                )
            self.stdout.write('Created: Footer with links')

        self.stdout.write(self.style.SUCCESS('\nHomepage sections seeded successfully!'))
        self.stdout.write(f'Total sections: {HomepageSection.objects.count()}')
        self.stdout.write(f'Active sections: {HomepageSection.objects.filter(is_active=True).count()}')
