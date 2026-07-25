from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Wishlist


@receiver([post_save, post_delete], sender=Wishlist)
def clear_wishlist_cache(sender, instance, **kwargs):
    cache.delete(f'wishlist_ids_{instance.user_id}')
