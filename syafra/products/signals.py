from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import (
    Category, InstagramFeedItem, Product, ProductImage, ProductSize, Testimonial,
    HomepageSection, HeroSlide, TrustBarItem, ShopByCategoryItem,
    FooterLink, NewsletterSubscriber, ProductCollection,
    ThemeSettings, WebsiteSettings,
)


def invalidate_homepage_cache():
    cache.delete('homepage_data')
    cache.delete('homepage_sections_v1')


def invalidate_catalog_cache():
    cache.delete_many(['all_categories', 'available_sizes'])


@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=ProductImage)
@receiver([post_save, post_delete], sender=InstagramFeedItem)
@receiver([post_save, post_delete], sender=Testimonial)
def clear_homepage_cache_on_content_change(sender, **kwargs):
    invalidate_homepage_cache()


@receiver([post_save, post_delete], sender=Category)
def clear_category_cache_on_change(sender, **kwargs):
    invalidate_homepage_cache()
    invalidate_catalog_cache()


@receiver([post_save, post_delete], sender=ProductSize)
def clear_size_cache_on_change(sender, **kwargs):
    invalidate_homepage_cache()
    invalidate_catalog_cache()


@receiver([post_save, post_delete], sender=HomepageSection)
@receiver([post_save, post_delete], sender=HeroSlide)
@receiver([post_save, post_delete], sender=TrustBarItem)
@receiver([post_save, post_delete], sender=ShopByCategoryItem)
@receiver([post_save, post_delete], sender=FooterLink)
@receiver([post_save, post_delete], sender=ProductCollection)
def clear_homepage_sections_cache(sender, **kwargs):
    invalidate_homepage_cache()


@receiver([post_save, post_delete], sender=ThemeSettings)
@receiver([post_save, post_delete], sender=WebsiteSettings)
def clear_theme_website_cache(sender, **kwargs):
    cache.delete('theme_settings_v1')
    cache.delete('website_settings_v1')
    invalidate_homepage_cache()
