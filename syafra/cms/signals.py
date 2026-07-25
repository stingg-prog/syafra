from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import SiteNavigation, AnnouncementBarConfig, PromoBanner, LegalPage


def clear_cms_context_cache():
    cache.delete('cms_navigation_context')
    cache.delete('cms_context_data')


@receiver([post_save, post_delete], sender=SiteNavigation)
def clear_navigation_cache(sender, **kwargs):
    clear_cms_context_cache()


@receiver([post_save, post_delete], sender=AnnouncementBarConfig)
@receiver([post_save, post_delete], sender=PromoBanner)
@receiver([post_save, post_delete], sender=LegalPage)
def clear_cms_cache(sender, **kwargs):
    clear_cms_context_cache()
