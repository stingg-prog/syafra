from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.db.models import Q, Max, Min, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import re

from .models import (
    Product, Category, InstagramPost, Testimonial,
    HomepageSection, NewsletterSubscriber, ProductCollection,
    ShopByCategoryItem, ContentPage, ContactMessage,
    ThemeSettings, WebsiteSettings,
)
from .forms import ContactForm
from orders.models import PaymentSettings


def home(request):
    sections = list(HomepageSection.objects.filter(is_active=True).order_by('display_order'))

    section_data = {}
    for section in sections:
        data = {'section': section}
        st = section.section_type

        if st == 'hero_slider':
            data['slides'] = list(section.hero_slides.filter(is_active=True).order_by('display_order'))
            data['secondary_cta_label'] = section.config.get('secondary_cta_label', '')
            data['secondary_cta_url'] = section.config.get('secondary_cta_url', '')

        elif st in ('product_collection', 'womens_tops', 'trending_now', 'best_sellers'):
            if section.collection:
                data['products'] = list(
                    section.collection.products.filter(stock__gt=0)
                    .select_related('category')[:12]
                )
            else:
                data['products'] = []

        elif st == 'shop_by_category':
            data['category_items'] = list(
                section.category_items.filter(is_active=True)
                .select_related('category')
                .order_by('display_order')[:2]
            )

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

    _COLLECTION_TYPES = frozenset({'product_collection', 'womens_tops', 'trending_now', 'best_sellers'})
    hide_ids = {s.id for s in sections
                if s.section_type in _COLLECTION_TYPES
                and not section_data.get(s.id, {}).get('products')}
    sections = [s for s in sections if s.id not in hide_ids]

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


SIZE_ORDER = {'XS': 0, 'S': 1, 'M': 2, 'L': 3, 'XL': 4, 'XXL': 5}


def shop(request):
    products = Product.objects.select_related('category').prefetch_related('sizes').all()

    search_query = request.GET.get('search', '').strip()
    category_slug = request.GET.get('category', '')
    size_filter = request.GET.get('size', '')
    stock_filter = request.GET.get('stock', '')
    in_stock = request.GET.get('in_stock', '')
    out_of_stock = request.GET.get('out_of_stock', '')
    brand_filter = ','.join(request.GET.getlist('brand'))
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort_by = request.GET.get('sort', 'newest')

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
        in_stock = '1'
    elif stock_filter == 'sold_out':
        out_of_stock = '1'

    in_stock_active = in_stock == '1'
    out_of_stock_active = out_of_stock == '1'
    if in_stock_active and not out_of_stock_active:
        products = products.filter(stock__gt=0)
    elif out_of_stock_active and not in_stock_active:
        products = products.filter(stock=0)

    if brand_filter:
        brand_list = [b.strip() for b in brand_filter.split(',') if b.strip()]
        if brand_list:
            products = products.filter(brand__in=brand_list)

    if min_price:
        try:
            from decimal import Decimal
            products = products.filter(price__gte=Decimal(str(min_price)))
        except Exception:
            pass

    if max_price:
        try:
            from decimal import Decimal
            products = products.filter(price__lte=Decimal(str(max_price)))
        except Exception:
            pass

    sort_map = {
        'newest': ['-created_at'],
        'oldest': ['created_at'],
        'price-asc': ['price'],
        'price-desc': ['-price'],
        'best_selling': ['-is_featured', '-created_at'],
        'popularity': ['-is_featured', '-created_at'],
    }
    order_fields = sort_map.get(sort_by, ['-created_at'])
    products = products.order_by(*order_fields)

    available_brands = list(
        Product.objects.values_list('brand', flat=True)
        .distinct().order_by('brand')
    )

    categories = cache.get('all_categories')
    if categories is None:
        categories = list(Category.objects.all().order_by('name'))
        cache.set('all_categories', categories, 3600)

    raw_sizes = cache.get('available_sizes')
    if raw_sizes is None:
        from products.models import ProductSize
        raw_sizes = list(
            ProductSize.objects.filter(stock__gt=0)
            .values_list('size', flat=True)
            .order_by().distinct()
        )
        cache.set('available_sizes', raw_sizes, 3600)
    available_sizes = sorted(raw_sizes, key=lambda s: SIZE_ORDER.get(s, 99))

    price_extents = products.aggregate(
        min_price=Min('price'), max_price=Max('price')
    )
    price_min = price_extents['min_price'] or 0
    price_max = price_extents['max_price'] or 0

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    active_filter_count = sum([
        1 if search_query else 0,
        1 if category_slug else 0,
        1 if size_filter else 0,
        1 if brand_filter else 0,
        1 if min_price else 0,
        1 if max_price else 0,
        1 if in_stock_active else 0,
        1 if out_of_stock_active else 0,
    ])

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    selected_brand_list = [b.strip() for b in brand_filter.split(',') if b.strip()]

    import urllib.parse
    current_params = request.GET.copy()

    def build_remove_url(remove_map):
        p = current_params.copy()
        for k, v in remove_map.items():
            if v is None:
                p.pop(k, None)
            else:
                p[k] = v
        return '?' + p.urlencode()

    active_filters = []
    if search_query:
        active_filters.append({
            'label': f'"{search_query}"',
            'url': build_remove_url({'search': None})
        })
    if category_slug:
        cat_name = ''
        for c in categories:
            if c.slug == category_slug:
                cat_name = c.name
                break
        active_filters.append({
            'label': cat_name,
            'url': build_remove_url({'category': None})
        })
    if size_filter:
        active_filters.append({
            'label': f'Size {size_filter}',
            'url': build_remove_url({'size': None})
        })
    if brand_filter:
        for b in selected_brand_list:
            remaining = [x for x in selected_brand_list if x != b]
            active_filters.append({
                'label': b,
                'url': build_remove_url({'brand': ','.join(remaining) if remaining else None})
            })
    if min_price or max_price:
        parts = []
        if min_price:
            parts.append(f'{currency}{min_price}')
        if max_price:
            parts.append(f'{currency}{max_price}')
        active_filters.append({
            'label': '–'.join(parts),
            'url': build_remove_url({'min_price': None, 'max_price': None})
        })
    if in_stock_active:
        active_filters.append({
            'label': 'In Stock',
            'url': build_remove_url({'in_stock': None})
        })
    if out_of_stock_active:
        active_filters.append({
            'label': 'Out of Stock',
            'url': build_remove_url({'out_of_stock': None})
        })

    suggested_products = []
    total_count = paginator.count
    if total_count == 0:
        suggested_qs = Product.objects.select_related('category').prefetch_related('sizes')
        if category_slug:
            suggested_qs = suggested_qs.filter(category__slug=category_slug)
        suggested_products = list(suggested_qs.order_by('-is_featured', '-created_at')[:4])

    page_start = (products.number - 1) * paginator.per_page + 1 if total_count > 0 else 0
    page_end = min(page_start + paginator.per_page - 1, total_count) if total_count > 0 else 0

    return render(request, 'shop.html', {
        'products': products,
        'categories': categories,
        'available_sizes': available_sizes,
        'available_brands': available_brands,
        'search_query': search_query,
        'selected_category': category_slug,
        'selected_size': size_filter,
        'in_stock': in_stock,
        'out_of_stock': out_of_stock,
        'selected_brand': brand_filter,
        'selected_brand_list': selected_brand_list,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'price_min': price_min,
        'price_max': price_max,
        'active_filter_count': active_filter_count,
        'active_filters': active_filters,
        'suggested_products': suggested_products,
        'page_start': page_start,
        'page_end': page_end,
        'total_count': total_count,
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
    get_object_or_404(Category, slug=slug)
    params = request.GET.copy()
    params['category'] = slug
    params.pop('page', None)
    return redirect(f"{reverse('products:shop')}?{params.urlencode()}")


def content_page(request, slug):
    page = get_object_or_404(ContentPage, slug=slug, is_active=True)
    meta_title = page.meta_title or f"{page.title} | {ThemeSettings.get_settings().store_name}"
    meta_description = page.meta_description or page.summary or WebsiteSettings.get_settings().seo_description or ''
    return render(request, 'pages/content_page.html', {
        'page': page,
        'meta_title': meta_title,
        'meta_description': meta_description,
    })


def contact(request):
    page = ContentPage.objects.filter(slug='contact-us', is_active=True).first()
    website = WebsiteSettings.get_settings()
    contact_details = {
        'email': website.contact_email,
        'phone': website.contact_phone,
        'address': website.business_address,
        'hours': website.business_hours,
        'whatsapp': website.whatsapp_number,
    }
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        message = ContactMessage.objects.create(
            name=form.cleaned_data['name'],
            email=form.cleaned_data['email'],
            phone=form.cleaned_data.get('phone', ''),
            subject=form.cleaned_data['subject'],
            message=form.cleaned_data['message'],
        )
        _send_contact_notification(message)
        from django.contrib import messages
        messages.success(request, 'Thank you! Your message has been received.')
        return redirect('products:contact')
    meta_title = 'Contact Us'
    if page:
        meta_title = page.meta_title or f"{page.title} | {ThemeSettings.get_settings().store_name}"
    return render(request, 'pages/contact.html', {
        'page': page,
        'form': form,
        'contact_details': {k: v for k, v in contact_details.items() if v},
        'meta_title': meta_title,
        'meta_description': page.meta_description if page else '',
    })


def track_order(request):
    result = None
    from orders.models import Order, PaymentSettings
    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'
    if request.method == 'POST':
        order_number = request.POST.get('order_number', '').strip()
        email = request.POST.get('email', '').strip()
        try:
            order = Order.objects.prefetch_related('items__product').get(pk=order_number, email=email)
            result = order
        except (Order.DoesNotExist, ValueError):
            result = None
    return render(request, 'pages/track_order.html', {
        'result': result,
        'currency': currency,
        'meta_title': 'Track Order',
        'meta_description': '',
    })


def _send_contact_notification(message):
    import logging
    logger = logging.getLogger(__name__)
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        website = WebsiteSettings.get_settings()
        if website.contact_email:
            send_mail(
                subject=f"Contact Form: {message.subject}",
                message=f"From: {message.name} ({message.email})\nPhone: {message.phone or 'Not provided'}\n\n{message.message}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[website.contact_email],
                fail_silently=False,
            )
    except Exception as e:
        logger.error(f"Failed to send contact notification for message {message.pk}: {e}")
