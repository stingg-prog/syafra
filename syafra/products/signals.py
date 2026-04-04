from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Category, InstagramPost, Product, ProductImage, ProductSize, Testimonial


def invalidate_homepage_cache():
    cache.delete('homepage_data')


def invalidate_catalog_cache():
    cache.delete_many(['all_categories', 'available_sizes'])


@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=ProductImage)
@receiver([post_save, post_delete], sender=InstagramPost)
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
