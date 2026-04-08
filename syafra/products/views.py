from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.db.models import Q, Max, Count
from .models import Product, Category, InstagramPost, Testimonial
from orders.models import PaymentSettings

INSTAGRAM_DEFAULT_LINK = 'https://www.instagram.com/syafra.thrift/'


def build_instagram_tiles(posts, limit=6):
    return [
        {
            'link': post.link or INSTAGRAM_DEFAULT_LINK,
            'image_url': post.image.url,
            'alt': f'Instagram post {index}',
        }
        for index, post in enumerate(posts[:limit], start=1)
        if post.image
    ]


def home(request):
    instagram_queryset = InstagramPost.objects.filter(is_active=True).exclude(image='')
    featured_stats = Product.objects.filter(is_featured=True, stock__gt=0).aggregate(
        count=Count('id'),
        latest=Max('updated_at'),
    )
    instagram_stats = instagram_queryset.aggregate(
        count=Count('id'),
        latest=Max('created_at'),
    )
    testimonial_stats = Testimonial.objects.filter(is_active=True).aggregate(
        count=Count('id'),
        latest=Max('created_at'),
    )

    featured_latest = int(featured_stats['latest'].timestamp()) if featured_stats['latest'] else 0
    instagram_latest = int(instagram_stats['latest'].timestamp()) if instagram_stats['latest'] else 0
    testimonial_latest = int(testimonial_stats['latest'].timestamp()) if testimonial_stats['latest'] else 0

    cache_key = (
        f"homepage_data_v4:"
        f"fp{featured_stats['count']}-{featured_latest}:"
        f"ig{instagram_stats['count']}-{instagram_latest}:"
        f"ts{testimonial_stats['count']}-{testimonial_latest}"
    )
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        featured_products = (
            Product.objects.filter(is_featured=True, stock__gt=0)
            .select_related('category')
            .prefetch_related('sizes', 'images')[:8]
        )
        instagram_posts = instagram_queryset[:6]
        testimonials = Testimonial.objects.filter(is_active=True)[:3]
        
        payment_settings = PaymentSettings.get_settings()
        currency = payment_settings.currency_symbol if payment_settings else '₹'
        
        cached_data = {
            'featured_products': list(featured_products),
            'instagram_posts': build_instagram_tiles(instagram_posts),
            'testimonials': list(testimonials),
            'currency': currency,
        }
        cache.set(cache_key, cached_data, 300)
    
    return render(request, 'home.html', cached_data)


def shop(request):
    products = (
        Product.objects.select_related('category')
        .prefetch_related('sizes', 'images')
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
    related_products = Product.objects.filter(category=product.category).exclude(pk=pk)[:4]
    
    payment_settings = PaymentSettings.get_settings()
    currency = payment_settings.currency_symbol if payment_settings else '₹'
    
    wa_text = f'Hi, I am interested in {product.name} ({product.brand}). Is it available?'
    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products,
        'currency': currency,
        'whatsapp_product_message': wa_text,
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = (
        Product.objects.filter(category=category)
        .select_related('category')
        .prefetch_related('sizes', 'images')
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
