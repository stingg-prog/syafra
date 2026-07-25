from django.core.cache import cache
from .models import Wishlist

WISHLIST_CACHE_TIMEOUT = 300


def wishlist_ids(request):
    if request.user.is_authenticated:
        cache_key = f'wishlist_ids_{request.user.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        ids = set(
            Wishlist.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )
        count = len(ids)
        result = {'wishlisted_ids': ids, 'wishlist_count': count}
        cache.set(cache_key, result, WISHLIST_CACHE_TIMEOUT)
        return result
    return {'wishlisted_ids': set(), 'wishlist_count': 0}
