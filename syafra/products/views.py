from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.db.models import Q, Max, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import re

from .models import (
    Product, Category, InstagramPost, Testimonial,
    HomepageSection, NewsletterSubscriber, ProductCollection,
)
from orders.models import PaymentSettings


def home(request):
    sections = HomepageSection.objects.filter(is_active=True).order_by('display_order')

    section_data = {}
    for section in sections:
        data = {'section': section}
        st = section.section_type

        if st == 'hero_slider':
            data['slides'] = list(section.hero_slides.filter(is_active=True).order_by('display_order'))

        elif st in ('product_collection', 'womens_tops', 'trending_now', 'best_sellers'):
            if section.collection:
                data['products'] = list(
                    section.collection.products.filter(stock__gt=0)
                    .select_related('category')[:12]
                )
            else:
                data['products'] = []

        elif st == 'customer_reviews':
            max_items = section.config.get('max_items', 3)
            data['testimonials'] = list(Testimonial.objects.filter(is_active=True)[:max_items])

        elif st == 'instagram_feed':
            max_items = section.config.get('max_items', 6)
            data['posts'] = list(
                InstagramPost.objects.filter(is_active=True)
                .exclude(image='').exclude(image__isnull=True)[:max_items]
            )

        section_data[section.id] = data

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    context = {
        'sections': sections,
        'section_data': section_data,
        'currency': currency,
    }
    return render(request, 'home.html', context)


@require_POST
def newsletter_subscribe(request):
    email = request.POST.get('email', '').strip()
    if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return JsonResponse({'success': False, 'error': 'Valid email required.'}, status=400)

    subscriber, created = NewsletterSubscriber.objects.get_or_create(
        email__iexact=email,
        defaults={'source': 'homepage'}
    )
    if not created and not subscriber.is_active:
        subscriber.is_active = True
        subscriber.unsubscribed_at = None
        subscriber.save(update_fields=['is_active', 'unsubscribed_at'])

    return JsonResponse({'success': True, 'message': 'Subscribed!'})


def shop(request):
    products = (
        Product.objects.select_related('category')
        .prefetch_related('sizes')
        .all()
        .order_by('-created_at')
    )

    search_query = request.GET.get('search', '')
    category_slug = request.GET.get('category', '')
    size_filter = request.GET.get('size', '')
    stock_filter = request.GET.get('stock', '')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if size_filter:
        products = products.filter(sizes__size__iexact=size_filter).distinct()

    if stock_filter == 'in_stock':
        products = products.filter(stock__gt=0)
    elif stock_filter == 'sold_out':
        products = products.filter(stock=0)

    categories = cache.get('all_categories')
    if categories is None:
        categories = list(Category.objects.all())
        cache.set('all_categories', categories, 3600)

    available_sizes = cache.get('available_sizes')
    if available_sizes is None:
        from products.models import ProductSize
        available_sizes = list(ProductSize.objects.filter(stock__gt=0).values_list('size', flat=True).distinct())
        cache.set('available_sizes', available_sizes, 3600)

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    return render(request, 'shop.html', {
        'products': products,
        'categories': categories,
        'available_sizes': available_sizes,
        'search_query': search_query,
        'selected_category': category_slug,
        'selected_size': size_filter,
        'selected_stock': stock_filter,
        'currency': currency,
    })


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('sizes', 'images'),
        pk=pk
    )
    gallery_images = list(product.images.all())
    related_products = Product.objects.filter(category=product.category).exclude(pk=pk)[:4]
    primary_image_url = (
        product.image.url if product.image else (
            gallery_images[0].image.url if gallery_images else ""
        )
    )

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    wa_text = f'Hi, I am interested in {product.name} ({product.brand}). Is it available?'
    return render(request, 'product_detail.html', {
        'product': product,
        'gallery_images': gallery_images,
        'primary_image_url': primary_image_url,
        'related_products': related_products,
        'currency': currency,
        'whatsapp_product_message': wa_text,
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = (
        Product.objects.filter(category=category)
        .select_related('category')
        .prefetch_related('sizes')
        .order_by('-created_at')
    )

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    return render(request, 'shop.html', {
        'products': products,
        'categories': Category.objects.all(),
        'selected_category': slug,
        'currency': currency,
    })
