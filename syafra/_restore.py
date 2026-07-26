#!/usr/bin/env python
"""Restore missing database records for SYAFRA. READ-ONLY safe: uses get_or_create."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')
django.setup()

from products.models import (
    HomepageSection, HeroSlide, TrustBarItem, ShopByCategoryItem,
    FooterLink, ProductCollection, Category, ThemeSettings, WebsiteSettings
)
from orders.models import PaymentSettings, WhatsAppSettings
from cms.models import AnnouncementBarConfig, SiteNavigation
from django.contrib.auth import get_user_model

User = get_user_model()
results = []


def log(msg):
    print(msg)
    results.append(msg)


# ============================================================
# 1. HOMEPAGE SECTIONS
# ============================================================
log("=== Homepage Sections ===")

# Section 1: Announcement Bar
obj, created = HomepageSection.objects.get_or_create(
    section_type='announcement_bar',
    defaults={
        'title': 'FREE SHIPPING ON ORDERS OVER \u20b95000',
        'display_order': 1,
        'is_active': True,
        'config': {
            'text': 'FREE SHIPPING ON ORDERS OVER \u20b95000',
            'bg_color': '#000000',
            'text_color': '#FFFFFF',
        },
    }
)
log(f"  Announcement Bar: {'CREATED' if created else 'EXISTS'}")

# Section 2: Hero Slider
obj, created = HomepageSection.objects.get_or_create(
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
log(f"  Hero Slider: {'CREATED' if created else 'EXISTS'}")
if created:
    slides = [
        {'title': 'THE NEW EDIT', 'subtitle': 'NEW ARRIVALS',
         'description': 'Curated pieces. Distinctive silhouettes.',
         'button_text': 'SHOP NOW', 'button_url': '/shop/', 'overlay_opacity': 60},
        {'title': 'STYLE WITHOUT BOUNDARIES', 'subtitle': 'DISCOVER SYAFRA',
         'description': 'Curated fashion for every expression.',
         'button_text': 'DISCOVER SYAFRA', 'button_url': '/shop/', 'overlay_opacity': 60},
    ]
    for i, sd in enumerate(slides):
        HeroSlide.objects.get_or_create(section=obj, display_order=i, defaults=sd)
    log(f"    Created {len(slides)} hero slides")

# Section 3: Trust Bar
obj, created = HomepageSection.objects.get_or_create(
    section_type='trust_bar',
    defaults={'title': 'Trust Bar', 'display_order': 3, 'is_active': True}
)
log(f"  Trust Bar: {'CREATED' if created else 'EXISTS'}")
if created:
    items = [
        {'icon_svg': 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
         'title': 'Free Shipping', 'description': 'On orders over \u20b95000'},
        {'icon_svg': 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
         'title': 'Authenticity Guaranteed', 'description': '100% genuine products'},
        {'icon_svg': 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
         'title': 'Easy Returns', 'description': '7-day return policy'},
        {'icon_svg': 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
         'title': 'Secure Payment', 'description': '100% secure checkout'},
    ]
    for i, d in enumerate(items):
        TrustBarItem.objects.get_or_create(section=obj, title=d['title'], defaults={**d, 'display_order': i})
    log(f"    Created {len(items)} trust items")

# Section 4: Shop By Category
obj, created = HomepageSection.objects.get_or_create(
    section_type='shop_by_category',
    defaults={
        'title': 'Shop by Category', 'subtitle': 'Find Your Perfect Style',
        'display_order': 4, 'is_active': True,
    }
)
log(f"  Shop By Category: {'CREATED' if created else 'EXISTS'}")

# Section 5: Product Collection - The Jacket Edit
col, _ = ProductCollection.objects.get_or_create(
    name='The Jacket Edit',
    defaults={'description': 'Curated outerwear for every look.'}
)
obj, created = HomepageSection.objects.get_or_create(
    section_type='product_collection',
    defaults={
        'title': 'The Jacket Edit', 'subtitle': 'Curated Outerwear',
        'collection': col, 'display_order': 5, 'is_active': True,
        'config': {'max_items': 12, 'show_view_all': True, 'view_all_url': '/shop/'},
    }
)
log(f"  The Jacket Edit: {'CREATED' if created else 'EXISTS'}")

# Section 5b: Women's Tops
col, _ = ProductCollection.objects.get_or_create(
    name="Women's Tops",
    defaults={'description': "Curated women's vintage tops and blouses"}
)
obj, created = HomepageSection.objects.get_or_create(
    section_type='womens_tops',
    defaults={
        'title': "Women's Tops", 'subtitle': 'Vintage Elegance Redefined',
        'collection': col, 'display_order': 6, 'is_active': True,
        'config': {'max_items': 12, 'show_view_all': True, 'view_all_url': '/shop/'},
    }
)
log(f"  Women's Tops: {'CREATED' if created else 'EXISTS'}")

# Section 5c: Trending Now
col, _ = ProductCollection.objects.get_or_create(
    name='Trending Now',
    defaults={'description': 'Currently trending vintage pieces'}
)
obj, created = HomepageSection.objects.get_or_create(
    section_type='trending_now',
    defaults={
        'title': 'Trending Now', 'subtitle': 'What Everyone Is Wearing',
        'collection': col, 'display_order': 7, 'is_active': True,
        'config': {'max_items': 12, 'show_view_all': True, 'view_all_url': '/shop/'},
    }
)
log(f"  Trending Now: {'CREATED' if created else 'EXISTS'}")

# Section 5d: Best Sellers
col, _ = ProductCollection.objects.get_or_create(
    name='Best Sellers',
    defaults={'description': 'Most popular vintage pieces'}
)
obj, created = HomepageSection.objects.get_or_create(
    section_type='best_sellers',
    defaults={
        'title': 'Best Sellers', 'subtitle': 'Customer Favorites',
        'collection': col, 'display_order': 8, 'is_active': True,
        'config': {'max_items': 12, 'show_view_all': True, 'view_all_url': '/shop/'},
    }
)
log(f"  Best Sellers: {'CREATED' if created else 'EXISTS'}")

# Section 6: Promotional Banner
obj, created = HomepageSection.objects.get_or_create(
    section_type='promotional_banner',
    defaults={
        'title': 'Season Sale', 'subtitle': 'UP TO 40% OFF',
        'display_order': 9, 'is_active': True,
        'config': {
            'bg_color': '#1a1a1a', 'text_color': '#FFFFFF',
            'button_text': 'SHOP SALE', 'button_url': '/shop/',
        },
    }
)
log(f"  Promotional Banner: {'CREATED' if created else 'EXISTS'}")

# Section 7: Customer Reviews
obj, created = HomepageSection.objects.get_or_create(
    section_type='customer_reviews',
    defaults={
        'title': 'What Our Customers Say', 'subtitle': 'Trusted by Fashion Enthusiasts',
        'display_order': 10, 'is_active': True, 'config': {'max_items': 3},
    }
)
log(f"  Customer Reviews: {'CREATED' if created else 'EXISTS'}")

# Section 8: Instagram Feed
obj, created = HomepageSection.objects.get_or_create(
    section_type='instagram_feed',
    defaults={
        'title': '@syafra.thrift', 'subtitle': 'Follow Us on Instagram',
        'display_order': 11, 'is_active': True, 'config': {'max_items': 6},
    }
)
log(f"  Instagram Feed: {'CREATED' if created else 'EXISTS'}")

# Section 9: Newsletter
obj, created = HomepageSection.objects.get_or_create(
    section_type='newsletter',
    defaults={
        'title': 'Stay in the Loop',
        'subtitle': 'Subscribe for exclusive offers and new arrivals',
        'display_order': 12, 'is_active': True,
        'config': {'placeholder': 'Enter your email', 'button_text': 'SUBSCRIBE'},
    }
)
log(f"  Newsletter: {'CREATED' if created else 'EXISTS'}")

# Section 10: Footer
obj, created = HomepageSection.objects.get_or_create(
    section_type='footer',
    defaults={'title': 'Footer', 'display_order': 13, 'is_active': True}
)
log(f"  Footer: {'CREATED' if created else 'EXISTS'}")
if created:
    links = [
        {'column_heading': 'SHOP', 'label': 'All Products', 'url': '/shop/', 'display_order': 1},
        {'column_heading': 'SHOP', 'label': 'Leather Jackets', 'url': '/shop/?category=leather-jackets', 'display_order': 2},
        {'column_heading': 'SHOP', 'label': 'Denim Jackets', 'url': '/shop/?category=denim-jackets', 'display_order': 3},
        {'column_heading': 'SHOP', 'label': 'Bomber Jackets', 'url': '/shop/?category=bomber-jackets', 'display_order': 4},
        {'column_heading': 'HELP', 'label': 'Contact Us', 'url': '/contact/', 'display_order': 5},
        {'column_heading': 'HELP', 'label': 'Shipping Info', 'url': '/pages/shipping-returns/', 'display_order': 6},
        {'column_heading': 'HELP', 'label': 'Returns', 'url': '/pages/shipping-returns/', 'display_order': 7},
        {'column_heading': 'HELP', 'label': 'FAQ', 'url': '/pages/faq/', 'display_order': 8},
        {'column_heading': 'HELP', 'label': 'Size Guide', 'url': '/pages/size-guide/', 'display_order': 9},
        {'column_heading': 'HELP', 'label': 'Track Order', 'url': '/track-order/', 'display_order': 10},
        {'column_heading': 'COMPANY', 'label': 'About Us', 'url': '/pages/about-us/', 'display_order': 11},
        {'column_heading': 'COMPANY', 'label': 'Sustainability', 'url': '/pages/sustainability/', 'display_order': 12},
        {'column_heading': 'COMPANY', 'label': 'Privacy Policy', 'url': '/pages/privacy-policy/', 'display_order': 13},
        {'column_heading': 'COMPANY', 'label': 'Terms of Service', 'url': '/pages/terms-of-service/', 'display_order': 14},
    ]
    for ld in links:
        FooterLink.objects.get_or_create(section=obj, label=ld['label'], defaults=ld)
    log(f"    Created {len(links)} footer links")

log(f"\n  Total sections: {HomepageSection.objects.count()}")
log(f"  Active sections: {HomepageSection.objects.filter(is_active=True).count()}")

# ============================================================
# 2. CMS NAVIGATION
# ============================================================
log("\n=== CMS Navigation ===")

nav_items = [
    {'label': 'Shop', 'url': '/shop/', 'placement': 'header_center', 'display_order': 1},
    {'label': 'New Arrivals', 'url': '/shop/?sort=newest', 'placement': 'header_center', 'display_order': 2},
    {'label': 'Collections', 'url': '/shop/', 'placement': 'header_center', 'display_order': 3},
    {'label': 'About', 'url': '/pages/about-us/', 'placement': 'header_center', 'display_order': 4},
    {'label': 'Contact', 'url': '/contact/', 'placement': 'header_center', 'display_order': 5},
    {'label': 'Track Order', 'url': '/track-order/', 'placement': 'header_right', 'display_order': 1},
]

created_count = 0
for nd in nav_items:
    obj, created = SiteNavigation.objects.get_or_create(
        label=nd['label'],
        placement=nd['placement'],
        defaults={'url': nd['url'], 'display_order': nd['display_order'], 'is_active': True},
    )
    if created:
        created_count += 1

log(f"  Navigation items: {created_count} created, {SiteNavigation.objects.count()} total")

# ============================================================
# 3. ENSURE SUPERUSER EXISTS
# ============================================================
log("\n=== Superuser Check ===")
superusers = User.objects.filter(is_superuser=True)
if superusers.exists():
    log(f"  Superuser exists: {superusers.first().username}")
else:
    log("  WARNING: No superuser found!")

# ============================================================
# 4. FINAL VERIFICATION
# ============================================================
log("\n=== Final Counts ===")
log(f"  ThemeSettings: {ThemeSettings.objects.count()}")
log(f"  WebsiteSettings: {WebsiteSettings.objects.count()}")
log(f"  PaymentSettings: {PaymentSettings.objects.count()}")
log(f"  WhatsAppSettings: {WhatsAppSettings.objects.count()}")
log(f"  AnnouncementBarConfig: {AnnouncementBarConfig.objects.count()}")
log(f"  HomepageSection: {HomepageSection.objects.count()}")
log(f"  HeroSlide: {HeroSlide.objects.count()}")
log(f"  TrustBarItem: {TrustBarItem.objects.count()}")
log(f"  ProductCollection: {ProductCollection.objects.count()}")
log(f"  FooterLink: {FooterLink.objects.count()}")
log(f"  SiteNavigation: {SiteNavigation.objects.count()}")
log(f"  Users: {User.objects.count()}")
log(f"  Superusers: {User.objects.filter(is_superuser=True).count()}")

log("\n=== RESTORATION COMPLETE ===")
