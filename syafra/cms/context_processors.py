import logging
from django.db.models import Prefetch

logger = logging.getLogger(__name__)


def navigation_context(request):
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

    return {
        'header_nav': header_center,
        'header_right_nav': header_right,
        'header_mobile_nav': header_mobile,
        'footer_nav': footer_nav,
    }


def cms_context(request):
    from .models import AnnouncementBarConfig, PromoBanner, LegalPage

    try:
        announcement = AnnouncementBarConfig.get_settings()
    except Exception:
        announcement = None

    try:
        promo_banners = PromoBanner.objects.filter(is_active=True).order_by('display_order')
    except Exception:
        promo_banners = []

    try:
        legal_pages = LegalPage.objects.filter(is_active=True).order_by('display_order')
    except Exception:
        legal_pages = []

    return {
        'announcement_bar': announcement,
        'promo_banners': promo_banners,
        'legal_pages': legal_pages,
    }
