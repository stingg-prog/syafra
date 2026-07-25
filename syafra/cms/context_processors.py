import logging
from django.core.cache import cache
from django.db.models import Prefetch

logger = logging.getLogger(__name__)

NAVIGATION_CACHE_KEY = 'cms_navigation_context'
NAVIGATION_CACHE_TIMEOUT = 300
CMS_CONTEXT_CACHE_KEY = 'cms_context_data'
CMS_CONTEXT_CACHE_TIMEOUT = 300


def navigation_context(request):
    cached = cache.get(NAVIGATION_CACHE_KEY)
    if cached is not None:
        return cached

    from .models import SiteNavigation

    try:
        nav_items = SiteNavigation.objects.filter(
            is_active=True, parent__isnull=True
        ).select_related('parent').prefetch_related(
            Prefetch('children', queryset=SiteNavigation.objects.filter(is_active=True).order_by('display_order'))
        ).order_by('placement', 'display_order')

        header_center = [n for n in nav_items if n.placement == 'header_center']
        header_right = [n for n in nav_items if n.placement == 'header_right']
        header_mobile = [n for n in nav_items if n.placement == 'header_mobile']
        footer_nav = [n for n in nav_items if n.placement == 'footer']
    except Exception:
        header_center = []
        header_right = []
        header_mobile = []
        footer_nav = []

    result = {
        'header_nav': header_center,
        'header_right_nav': header_right,
        'header_mobile_nav': header_mobile,
        'footer_nav': footer_nav,
    }
    cache.set(NAVIGATION_CACHE_KEY, result, NAVIGATION_CACHE_TIMEOUT)
    return result


def cms_context(request):
    cached = cache.get(CMS_CONTEXT_CACHE_KEY)
    if cached is not None:
        return cached

    from .models import AnnouncementBarConfig, PromoBanner, LegalPage

    try:
        announcement = AnnouncementBarConfig.get_settings()
    except Exception:
        announcement = None

    try:
        promo_banners = list(PromoBanner.objects.filter(is_active=True).order_by('display_order'))
    except Exception:
        promo_banners = []

    try:
        legal_pages = list(LegalPage.objects.filter(is_active=True).order_by('display_order'))
    except Exception:
        legal_pages = []

    result = {
        'announcement_bar': announcement,
        'promo_banners': promo_banners,
        'legal_pages': legal_pages,
    }
    cache.set(CMS_CONTEXT_CACHE_KEY, result, CMS_CONTEXT_CACHE_TIMEOUT)
    return result
