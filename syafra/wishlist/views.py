from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from orders.models import PaymentSettings
from products.models import Product

from .models import Wishlist


@login_required
def wishlist_page(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product__category')

    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'oldest':
        items = items.order_by('created_at')
    elif sort_by == 'price-asc':
        items = items.order_by('product__price')
    elif sort_by == 'price-desc':
        items = items.order_by('-product__price')
    else:
        items = items.order_by('-created_at')

    paginator = Paginator(items, 12)
    page = request.GET.get('page', 1)
    try:
        items_page = paginator.page(page)
    except PageNotAnInteger:
        items_page = paginator.page(1)
    except EmptyPage:
        items_page = paginator.page(paginator.num_pages)

    total_count = paginator.count
    page_start = (items_page.number - 1) * paginator.per_page + 1 if total_count > 0 else 0
    page_end = min(page_start + paginator.per_page - 1, total_count) if total_count > 0 else 0

    try:
        payment_settings = PaymentSettings.objects.first()
        currency = payment_settings.currency_symbol if payment_settings else '\u20b9'
    except Exception:
        currency = '\u20b9'

    return render(request, 'wishlist/wishlist.html', {
        'wishlist_items': items_page,
        'total_count': total_count,
        'page_start': page_start,
        'page_end': page_end,
        'sort_by': sort_by,
        'currency': currency,
    })


@require_POST
@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    _, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product,
    )
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({
        'success': True,
        'wishlisted': True,
        'count': count,
        'message': 'Added to wishlist.' if created else 'Already in wishlist.',
    })


@require_POST
@login_required
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    deleted, _ = Wishlist.objects.filter(
        user=request.user,
        product=product,
    ).delete()
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({
        'success': True,
        'wishlisted': False,
        'count': count,
        'message': 'Removed from wishlist.' if deleted else 'Not in wishlist.',
    })


@login_required
def wishlist_status(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    wishlisted = Wishlist.objects.filter(
        user=request.user,
        product=product,
    ).exists()
    return JsonResponse({
        'success': True,
        'wishlisted': wishlisted,
    })


@login_required
def wishlist_count(request):
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({
        'success': True,
        'count': count,
    })
