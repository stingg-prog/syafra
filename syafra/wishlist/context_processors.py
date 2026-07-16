from .models import Wishlist


def wishlist_ids(request):
    if request.user.is_authenticated:
        ids = set(
            Wishlist.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )
    else:
        ids = set()
    return {'wishlisted_ids': ids}
