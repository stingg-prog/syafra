from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.contrib import messages
from django.db.models import F, Q, Max, Min, Count
from django.http import Http404, JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
import json
import re

from .models import (
    Product, ProductSize, Category, InstagramFeedItem, Testimonial,
    HomepageSection, NewsletterSubscriber, ProductCollection,
    ShopByCategoryItem, ContentPage, ContactMessage,
    ThemeSettings, WebsiteSettings, HeroSlide,
)
from .forms import ContactForm
from orders.models import PaymentSettings


CACHE_KEY_THEME = 'syafra_theme_settings'
CACHE_TTL = 300


def _get_theme():
    data = cache.get(CACHE_KEY_THEME)
    if data is None:
        data = ThemeSettings.get_settings()
        cache.set(CACHE_KEY_THEME, data, CACHE_TTL)
    return data


def _get_active_sections():
    now = timezone.now()
    qs = HomepageSection.objects.filter(is_active=True).order_by('display_order')
    active = []
    for s in qs:
        if s.publish_at and s.publish_at > now:
            continue
        if s.unpublish_at and s.unpublish_at <= now:
            continue
        active.append(s)
    return active


def home(request):
    sections = _get_active_sections()
    section_data = {}

    for section in sections:
        data = {'section': section}
        st = section.section_type

        if st == 'hero_slider':
            data['slides'] = list(section.hero_slides.filter(is_active=True).order_by('display_order'))
            data['secondary_cta_label'] = section.config.get('secondary_cta_label', '')
            data['secondary_cta_url'] = section.config.get('secondary_cta_url', '')
            data['autoplay'] = section.config.get('autoplay', True)
            data['autoplay_speed'] = section.config.get('autoplay_speed', 5000)
            data['transition_speed'] = section.config.get('transition_speed', 600)
            data['transition_type'] = section.config.get('transition_type', '')

        elif st in ('product_collection', 'womens_tops', 'trending_now', 'best_sellers',
                    'featured_products', 'new_arrivals', 'trending_products', 'jackets',
                    'flash_sale'):
            if section.collection:
                limit = section.config.get('max_products', 12)
                data['products'] = list(
                    section.collection.products.filter(stock__gt=0)
                    .select_related('category')[:limit]
                )
            else:
                data['products'] = []

        elif st == 'hero_banner':
            data['products'] = list(
                section.collection.products.filter(stock__gt=0)
                .select_related('category')[:8]
            ) if section.collection else []

        elif st == 'shop_by_category':
            data['category_items'] = list(
                section.category_items.filter(is_active=True)
                .select_related('category')
                .order_by('display_order')[:4]
            )

        elif st == 'customer_reviews':
            max_items = section.config.get('max_items', 3)
            data['testimonials'] = list(Testimonial.objects.filter(is_active=True).order_by('display_order')[:max_items])

        elif st == 'instagram_feed':
            max_items = section.config.get('max_items', 6)
            data['posts'] = list(
                InstagramFeedItem.objects.filter(is_active=True)
                .exclude(image='').exclude(image__isnull=True)[:max_items]
            )

        elif st == 'brands':
            brand_ids = section.config.get('brand_ids', '')
            from cms.models import Brand
            qs = Brand.objects.filter(is_active=True).order_by('display_order')
            if brand_ids:
                ids = [int(x.strip()) for x in brand_ids.split(',') if x.strip().isdigit()]
                if ids:
                    qs = qs.filter(id__in=ids)
            data['brands'] = list(qs)

        elif st == 'collections':
            from cms.models import Collection
            data['collections'] = list(
                Collection.objects.filter(is_active=True)
                .prefetch_related('collection_products__product')
                .order_by('display_order')[:8]
            )

        elif st == 'lookbook':
            from cms.models import Lookbook
            data['lookbooks'] = list(
                Lookbook.objects.filter(is_published=True).order_by('display_order', '-created_at')[:6]
            )

        elif st == 'faq_section':
            from cms.models import FAQItem, FAQCategory
            cat_id = section.config.get('faq_category_id', '')
            qs = FAQItem.objects.filter(is_active=True).order_by('display_order')
            if cat_id:
                qs = qs.filter(category_id=int(cat_id))
            data['faq_items'] = list(qs)

        elif st in ('recently_viewed', 'recommended_products'):
            limit = section.config.get('max_products', 8)
            data['products'] = list(
                Product.objects.filter(stock__gt=0, is_featured=True)
                .select_related('category')[:limit]
            ) if st == 'recommended_products' else []

        section_data[section.id] = data

    _COLLECTION_TYPES = frozenset({
        'product_collection', 'womens_tops', 'trending_now', 'best_sellers',
        'featured_products', 'new_arrivals', 'trending_products', 'jackets',
        'flash_sale', 'recently_viewed', 'recommended_products',
    })
    hide_ids = {s.id for s in sections
                if s.section_type in _COLLECTION_TYPES
                and not section_data.get(s.id, {}).get('products')}
    hide_ids |= {s.id for s in sections
                 if s.section_type == 'shop_by_category'
                 and not section_data.get(s.id, {}).get('category_items')}
    hide_ids |= {s.id for s in sections
                 if s.section_type == 'customer_reviews'
                 and not section_data.get(s.id, {}).get('testimonials')}
    hide_ids |= {s.id for s in sections
                 if s.section_type == 'instagram_feed'
                 and not section_data.get(s.id, {}).get('posts')}
    sections = [s for s in sections if s.id not in hide_ids]

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    context = {
        'sections': sections,
        'section_data': section_data,
        'currency': currency,
    }
    return render(request, 'home.html', context)


@staff_member_required
@never_cache
def admin_preview(request, model_name, object_id):
    from django.template.response import TemplateResponse

    if model_name == 'homepagesection':
        return section_preview(request, object_id)

    elif model_name == 'blogpost':
        from cms.models import BlogPost
        obj = get_object_or_404(BlogPost, pk=object_id)
        return render(request, 'admin_preview/blog_post.html', {'post': obj})

    elif model_name == 'faqcategory':
        from cms.models import FAQCategory
        obj = get_object_or_404(FAQCategory, pk=object_id)
        items = obj.items.filter(is_active=True).order_by('display_order')
        return render(request, 'admin_preview/faq.html', {'category': obj, 'items': items})

    elif model_name == 'faqitem':
        from cms.models import FAQItem
        obj = get_object_or_404(FAQItem, pk=object_id)
        return render(request, 'admin_preview/faq.html', {'single_item': obj, 'items': [obj]})

    elif model_name == 'lookbook':
        from cms.models import Lookbook
        obj = get_object_or_404(Lookbook, pk=object_id)
        return render(request, 'admin_preview/lookbook.html', {'lookbook': obj})

    elif model_name == 'promobanner':
        from cms.models import PromoBanner
        obj = get_object_or_404(PromoBanner, pk=object_id)
        return render(request, 'admin_preview/promo_banner.html', {'banner': obj})

    elif model_name == 'announcementbarconfig':
        from cms.models import AnnouncementBarConfig
        obj = AnnouncementBarConfig.get_settings()
        return render(request, 'admin_preview/announcement_bar.html', {'announcement': obj})

    elif model_name == 'seosettings':
        from cms.models import SEOSettings
        obj = get_object_or_404(SEOSettings, pk=object_id)
        page_type = obj.get_page_type_display()
        return render(request, 'admin_preview/seo.html', {'seo': obj, 'page_type': page_type})

    elif model_name == 'legalpage':
        from cms.models import LegalPage
        obj = get_object_or_404(LegalPage, pk=object_id)
        return render(request, 'admin_preview/legal_page.html', {'page': obj})

    elif model_name == 'collection':
        from cms.models import Collection
        obj = get_object_or_404(Collection, pk=object_id)
        products = obj.collection_products.select_related('product').order_by('display_order')[:12]
        return render(request, 'admin_preview/collection.html', {'collection': obj, 'collection_products': products})

    elif model_name == 'brand':
        from cms.models import Brand
        obj = get_object_or_404(Brand, pk=object_id)
        return render(request, 'admin_preview/brand.html', {'brand': obj})

    elif model_name == 'productlabel':
        from cms.models import ProductLabel
        obj = get_object_or_404(ProductLabel, pk=object_id)
        return render(request, 'admin_preview/product_label.html', {'label': obj})

    elif model_name == 'productbadge':
        from cms.models import ProductBadge
        obj = get_object_or_404(ProductBadge, pk=object_id)
        return render(request, 'admin_preview/product_badge.html', {'badge': obj})

    elif model_name == 'sizechart':
        from cms.models import SizeChart
        obj = get_object_or_404(SizeChart, pk=object_id)
        return render(request, 'admin_preview/size_chart.html', {'size_chart': obj})

    elif model_name == 'careinstruction':
        from cms.models import CareInstruction
        obj = get_object_or_404(CareInstruction, pk=object_id)
        return render(request, 'admin_preview/care_instruction.html', {'care': obj})

    elif model_name == 'themesettings':
        from products.models import ThemeSettings
        return render(request, 'home.html')

    elif model_name == 'promotionalpopup':
        from cms.models import PromotionalPopup
        obj = get_object_or_404(PromotionalPopup, pk=object_id)
        return render(request, 'admin_preview/popup.html', {'popup': obj})

    elif model_name == 'contentpage':
        from products.models import ContentPage
        obj = get_object_or_404(ContentPage, pk=object_id)
        return render(request, 'admin_preview/legal_page.html', {'page': obj})

    raise Http404('Unknown model for preview')


@staff_member_required
@never_cache
def section_preview(request, section_id):
    section = get_object_or_404(HomepageSection, pk=section_id)
    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'
    section_data = {}
    data = {'section': section}
    st = section.section_type

    if st == 'hero_slider':
        data['slides'] = list(section.hero_slides.filter(is_active=True).order_by('display_order'))
        data['secondary_cta_label'] = section.config.get('secondary_cta_label', '')
        data['secondary_cta_url'] = section.config.get('secondary_cta_url', '')
        data['autoplay'] = False
    elif st in ('product_collection', 'womens_tops', 'trending_now', 'best_sellers',
                'featured_products', 'new_arrivals', 'trending_products', 'jackets', 'flash_sale'):
        if section.collection:
            data['products'] = list(section.collection.products.filter(stock__gt=0).select_related('category')[:12])
        else:
            data['products'] = []
    elif st == 'shop_by_category':
        data['category_items'] = list(
            section.category_items.filter(is_active=True).select_related('category').order_by('display_order')[:4]
        )
    elif st == 'customer_reviews':
        max_items = section.config.get('max_items', 3)
        data['testimonials'] = list(Testimonial.objects.filter(is_active=True)[:max_items])
    elif st == 'instagram_feed':
        max_items = section.config.get('max_items', 6)
        data['posts'] = list(InstagramFeedItem.objects.filter(is_active=True).exclude(image='').exclude(image__isnull=True)[:max_items])
    elif st == 'brands':
        from cms.models import Brand
        data['brands'] = list(Brand.objects.filter(is_active=True).order_by('display_order'))
    elif st == 'collections':
        from cms.models import Collection
        data['collections'] = list(Collection.objects.filter(is_active=True).order_by('display_order')[:8])
    elif st == 'lookbook':
        from cms.models import Lookbook
        data['lookbooks'] = list(Lookbook.objects.filter(is_published=True).order_by('display_order', '-created_at')[:6])
    elif st == 'faq_section':
        from cms.models import FAQItem
        data['faq_items'] = list(FAQItem.objects.filter(is_active=True).order_by('display_order'))
    elif st in ('recently_viewed', 'recommended_products'):
        limit = section.config.get('max_products', 8)
        data['products'] = list(Product.objects.filter(stock__gt=0, is_featured=True).select_related('category')[:limit])

    section_data[section.id] = data

    context = {
        'sections': [section],
        'section_data': section_data,
        'currency': currency,
        'is_preview': True,
    }
    return render(request, 'home.html', context)


@staff_member_required
def theme_export(request):
    theme = ThemeSettings.get_settings()
    data = theme.export_to_dict()
    response = HttpResponse(
        json.dumps(data, indent=2),
        content_type='application/json',
    )
    response['Content-Disposition'] = 'attachment; filename="syafra-theme.json"'
    return response


@csrf_exempt
@staff_member_required
def theme_import(request):
    if request.method == 'POST':
        try:
            if request.FILES.get('file'):
                data = json.loads(request.FILES['file'].read())
            else:
                data = json.loads(request.body)
            theme = ThemeSettings.get_settings()
            theme.import_from_dict(data)
            cache.delete(CACHE_KEY_THEME)
            messages.success(request, 'Theme settings imported successfully.')
        except Exception as e:
            messages.error(request, f'Import failed: {e}')
        return redirect('admin:products_themesettings_change', args=[1])
    return HttpResponse('Method not allowed', status=405)


@staff_member_required
def theme_reset(request):
    if request.method == 'POST':
        theme = ThemeSettings.get_settings()
        theme.delete()
        theme = ThemeSettings.get_settings()
        cache.delete(CACHE_KEY_THEME)
        messages.success(request, 'Theme settings reset to defaults.')
        return redirect('admin:products_themesettings_change', args=[1])
    return HttpResponse('Method not allowed', status=405)


@staff_member_required
def backup_list(request):
    from cms.models import ThemeBackup
    backups = ThemeBackup.objects.all().order_by('-created_at')
    return render(request, 'admin/theme_backups.html', {'backups': backups})


@staff_member_required
def backup_create(request):
    if request.method == 'POST':
        from cms.models import ThemeBackup
        theme = ThemeSettings.get_settings()
        name = request.POST.get('name', f'Backup {timezone.now().strftime("%Y-%m-%d %H:%M")}')
        ThemeBackup.objects.create(
            name=name,
            data=theme.export_to_dict(),
            created_by=request.user,
        )
        messages.success(request, f'Backup "{name}" created.')
        return redirect('admin:products_themesettings_change', args=[1])
    return HttpResponse('Method not allowed', status=405)


@staff_member_required
def backup_restore(request, backup_id):
    if request.method == 'POST':
        from cms.models import ThemeBackup
        backup = get_object_or_404(ThemeBackup, pk=backup_id)
        theme = ThemeSettings.get_settings()
        theme.import_from_dict(backup.data)
        cache.delete(CACHE_KEY_THEME)
        messages.success(request, f'Backup "{backup.name}" restored.')
        return redirect('admin:products_themesettings_change', args=[1])
    return HttpResponse('Method not allowed', status=405)


@staff_member_required
def backup_delete(request, backup_id):
    if request.method == 'POST':
        from cms.models import ThemeBackup
        backup = get_object_or_404(ThemeBackup, pk=backup_id)
        backup.delete()
        messages.success(request, f'Backup "{backup.name}" deleted.')
        return redirect('admin:products_themesettings_change', args=[1])
    return HttpResponse('Method not allowed', status=405)


@require_POST
def newsletter_subscribe(request):
    email = request.POST.get('email', '').strip().lower()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Valid email required.'}, status=400)
        messages.error(request, 'Please enter a valid email address.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    subscriber, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={'source': 'homepage'}
    )

    if created:
        msg = 'Thank you for subscribing to SYAFRA.'
    else:
        if subscriber.is_active:
            msg = 'You are already subscribed!'
        else:
            subscriber.is_active = True
            subscriber.unsubscribed_at = None
            subscriber.save()
            msg = 'Welcome back! You have been resubscribed.'

    if is_ajax:
        return JsonResponse({'success': True, 'message': msg})
    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', '/'))


SIZE_ORDER = {'XS': 0, 'S': 1, 'M': 2, 'L': 3, 'XL': 4, 'XXL': 5}


def _url_remove_param(request, key, value=None):
    params = request.GET.copy()
    if value is not None:
        values = params.getlist(key)
        if value in values:
            values.remove(value)
        if values:
            params.setlist(key, values)
        else:
            params.pop(key, None)
    else:
        params.pop(key, None)
    return params.urlencode()


def shop(request):
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort', 'newest')
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    brand_list = request.GET.getlist('brand')
    selected_size = request.GET.get('size')
    in_stock = request.GET.get('in_stock')
    out_of_stock = request.GET.get('out_of_stock')

    theme = _get_theme()
    per_page = theme.products_per_page if theme else 12

    products = Product.objects.all()
    products = products.filter(stock__gt=0)

    if category_slug:
        try:
            category = Category.objects.get(slug=category_slug)
            products = products.filter(category=category)
        except Category.DoesNotExist:
            pass

    if brand_list:
        products = products.filter(brand__in=brand_list)

    if selected_size:
        products = products.filter(sizes__size__iexact=selected_size, sizes__stock__gt=0)

    if in_stock == '1' and out_of_stock != '1':
        products = products.filter(stock__gt=0)
    elif out_of_stock == '1' and in_stock != '1':
        products = products.filter(stock=0)
    elif in_stock == '1' and out_of_stock == '1':
        pass

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    if sort_by == 'price_low' or sort_by == 'price-asc':
        products = products.order_by('price', 'name')
    elif sort_by == 'price_high' or sort_by == 'price-desc':
        products = products.order_by('-price', 'name')
    elif sort_by == 'name_az':
        products = products.order_by('name')
    elif sort_by == 'name_za':
        products = products.order_by('-name')
    elif sort_by == 'oldest':
        products = products.order_by('created_at')
    elif sort_by == 'best_selling':
        products = products.order_by('-is_featured', '-created_at')
    elif sort_by == 'popularity':
        products = products.order_by('-is_featured', '-created_at')
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, per_page)
    page = request.GET.get('page', 1)

    try:
        product_page = paginator.page(page)
    except PageNotAnInteger:
        product_page = paginator.page(1)
    except EmptyPage:
        product_page = paginator.page(paginator.num_pages)

    categories = Category.objects.annotate(product_count=Count('products')).order_by('name')
    price_range = Product.objects.filter(stock__gt=0).aggregate(
        min_price=Min('price'), max_price=Max('price')
    )

    available_brands = list(
        Product.objects.filter(stock__gt=0)
        .exclude(brand='').exclude(brand__isnull=True)
        .values_list('brand', flat=True).distinct().order_by('brand')
    )
    raw_sizes = list(
        ProductSize.objects.filter(stock__gt=0)
        .values_list('size', flat=True).distinct().order_by()
    )
    available_sizes = sorted(raw_sizes, key=lambda s: SIZE_ORDER.get(s, 99))

    total_count = paginator.count
    page_start = (product_page.number - 1) * paginator.per_page + 1 if total_count > 0 else 0
    page_end = min(page_start + paginator.per_page - 1, total_count) if total_count > 0 else 0

    active_filters = []
    if category_slug:
        active_filters.append({'label': f'Category: {category_slug}', 'url': f'?{_url_remove_param(request, "category")}'})
    for b in brand_list:
        active_filters.append({'label': f'Brand: {b}', 'url': f'?{_url_remove_param(request, "brand", b)}'})
    if selected_size:
        active_filters.append({'label': f'Size: {selected_size}', 'url': f'?{_url_remove_param(request, "size")}'})
    if min_price:
        active_filters.append({'label': f'Min: ₹{min_price}', 'url': f'?{_url_remove_param(request, "min_price")}'})
    if max_price:
        active_filters.append({'label': f'Max: ₹{max_price}', 'url': f'?{_url_remove_param(request, "max_price")}'})
    if search_query:
        active_filters.append({'label': f'Search: {search_query}', 'url': f'?{_url_remove_param(request, "q")}'})

    suggested_products = []
    if total_count == 0:
        suggested_qs = Product.objects.filter(stock__gt=0)
        if category_slug:
            suggested_qs = suggested_qs.filter(category__slug=category_slug)
        suggested_products = list(suggested_qs.order_by('-is_featured', '-created_at')[:4])

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    context = {
        'products': product_page,
        'categories': categories,
        'price_range': price_range,
        'sort_by': sort_by,
        'search_query': search_query,
        'selected_category': category_slug,
        'selected_brand_list': brand_list,
        'selected_size': selected_size,
        'in_stock': in_stock,
        'out_of_stock': out_of_stock,
        'min_price': min_price,
        'max_price': max_price,
        'available_brands': available_brands,
        'available_sizes': available_sizes,
        'total_count': total_count,
        'page_start': page_start,
        'page_end': page_end,
        'active_filters': active_filters,
        'active_filter_count': len(active_filters),
        'suggested_products': suggested_products,
        'currency': currency,
    }
    return render(request, 'shop.html', context)


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('sizes', 'images'),
        pk=pk
    )
    product.views = F('views') + 1
    product.save(update_fields=['views'])
    product.refresh_from_db()

    gallery_images = list(product.images.all())
    primary_image_url = (
        product.image.url if product.image else (
            gallery_images[0].image.url if gallery_images else ''
        )
    )

    related = Product.objects.filter(
        category=product.category, stock__gt=0
    ).exclude(pk=product.pk)[:4]

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    request_scheme = 'https' if request.is_secure() else 'http'
    product_url = f'{request_scheme}://{request.get_host()}{product.get_absolute_url()}'

    og_image_url = primary_image_url
    og_description = (
        product.description[:200] if product.description
        else f'Shop {product.name} at SYAFRA. Premium vintage streetwear.'
    )
    share_text = (
        f'\u2728 {product.name}\n'
        f'\U0001f4b0 {currency}{product.price}\n'
        f'\U0001f6cd\ufe0f Shop Now:\n'
        f'{product_url}'
    )

    context = {
        'product': product,
        'gallery_images': gallery_images,
        'primary_image_url': primary_image_url,
        'related_products': related,
        'currency': currency,
        'og_image_url': og_image_url,
        'og_description': og_description,
        'product_url': product_url,
        'share_text': share_text,
    }
    return render(request, 'product_detail.html', context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products_list = Product.objects.filter(category=category, stock__gt=0).order_by('-created_at')

    selected_size = request.GET.get('size')
    if selected_size:
        products_list = products_list.filter(sizes__size__iexact=selected_size, sizes__stock__gt=0)

    theme = _get_theme()
    per_page = theme.products_per_page if theme else 12

    paginator = Paginator(products_list, per_page)
    page = request.GET.get('page', 1)

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    categories = Category.objects.annotate(product_count=Count('products')).order_by('name')
    price_range = Product.objects.filter(stock__gt=0).aggregate(
        min_price=Min('price'), max_price=Max('price')
    )
    available_brands = list(
        Product.objects.filter(stock__gt=0)
        .exclude(brand='').exclude(brand__isnull=True)
        .values_list('brand', flat=True).distinct().order_by('brand')
    )
    raw_sizes = list(
        ProductSize.objects.filter(stock__gt=0)
        .values_list('size', flat=True).distinct().order_by()
    )
    available_sizes = sorted(raw_sizes, key=lambda s: SIZE_ORDER.get(s, 99))
    active_filters = []
    if selected_size:
        active_filters.append({'label': f'Size: {selected_size}', 'url': f'?{_url_remove_param(request, "size")}'})
    total_count = paginator.count
    page_start = (products.number - 1) * paginator.per_page + 1 if total_count > 0 else 0
    page_end = min(page_start + paginator.per_page - 1, total_count) if total_count > 0 else 0

    suggested_products = []
    if total_count == 0:
        suggested_products = list(
            Product.objects.filter(stock__gt=0, category=category)
            .order_by('-is_featured', '-created_at')[:4]
        )

    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    context = {
        'category': category,
        'products': products,
        'selected_category': category.slug,
        'categories': categories,
        'price_range': price_range,
        'sort_by': 'newest',
        'search_query': '',
        'selected_brand_list': [],
        'selected_size': selected_size,
        'in_stock': '',
        'out_of_stock': '',
        'min_price': '',
        'max_price': '',
        'available_brands': available_brands,
        'available_sizes': available_sizes,
        'total_count': total_count,
        'page_start': page_start,
        'page_end': page_end,
        'active_filters': active_filters,
        'active_filter_count': len(active_filters),
        'suggested_products': suggested_products,
        'currency': currency,
    }
    return render(request, 'shop.html', context)


def content_page(request, slug):
    page = get_object_or_404(ContentPage, slug=slug, is_active=True)
    meta_title = page.meta_title or f"{page.title} | {ThemeSettings.get_settings().store_name}"
    meta_description = page.meta_description or page.summary or ''
    context = {
        'page': page,
        'meta_title': meta_title,
        'meta_description': meta_description,
    }
    return render(request, 'pages/content_page.html', context)


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
        ContactMessage.objects.create(
            name=form.cleaned_data['name'],
            email=form.cleaned_data['email'],
            phone=form.cleaned_data.get('phone', ''),
            subject=form.cleaned_data['subject'],
            message=form.cleaned_data['message'],
        )
        messages.success(request, 'Thank you for your message! We will get back to you soon.')
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
    from orders.models import Order
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
