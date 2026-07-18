from .models import Wishlist


def wishlist_ids(request):
    if request.user.is_authenticated:
        ids = set(
            Wishlist.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )
        count = len(ids)
    else:
        ids = set()
        count = 0
    return {'wishlisted_ids': ids, 'wishlist_count': count}
