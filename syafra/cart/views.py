# Cart modification endpoints are intentionally POST-only to prevent unsafe side effects over GET.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Cart, CartItem
from products.models import Product, ProductSize
from orders.models import PaymentSettings

# Single reusable constant for free shipping threshold (no DB field exists)
FREE_SHIPPING_THRESHOLD = 999


@login_required
def cart_view(request):
    cart = Cart.get_for_user(request.user)
    # Single pass over prefetched rows avoids N+1 queries from Cart.total hitting item.subtotal.
    # select_related('product__category') avoids extra query for item.product.category
    items = list(cart.items.select_related('product__category').all())
    total = sum(item.quantity * item.product.price for item in items)

    payment_settings = PaymentSettings.get_settings()
    if payment_settings:
        razorpay_key_id = payment_settings.resolved_razorpay_key_id
        razorpay_key_secret = payment_settings.resolved_razorpay_key_secret
        online_checkout_available = bool(
            payment_settings.is_active and razorpay_key_id and razorpay_key_secret
        )
    else:
        razorpay_key_id, razorpay_key_secret = PaymentSettings.get_env_razorpay_credentials()
        online_checkout_available = bool(razorpay_key_id and razorpay_key_secret)
    upi_checkout_available = bool(
        payment_settings and payment_settings.upi_enabled and payment_settings.upi_id
    )
    checkout_available = bool(online_checkout_available or upi_checkout_available)
    if not checkout_available:
        if payment_settings and payment_settings.is_active:
            checkout_notice = 'Payment setup is incomplete. Please configure Razorpay API keys.'
        else:
            checkout_notice = (
                payment_settings.payment_disabled_message
                if payment_settings
                else 'Online payments are currently unavailable.'
            )
    else:
        checkout_notice = ''
    currency = payment_settings.currency_symbol if payment_settings else '₹'

    # Free shipping calculation
    free_shipping_threshold = FREE_SHIPPING_THRESHOLD
    free_shipping_remaining = max(0, free_shipping_threshold - float(total))
    free_shipping_percent = min(100, int((float(total) / free_shipping_threshold) * 100)) if free_shipping_threshold > 0 else 100

    # Recommended products queryset (efficient, 6 max)
    cart_product_ids = [item.product_id for item in items]
    cart_category_ids = list(set(
        item.product.category_id for item in items if item.product.category_id
    ))
    cart_brands = list(set(
        item.product.brand for item in items if item.product.brand
    ))

    recommended = []
    base_qs = Product.objects.filter(stock__gt=0).exclude(id__in=cart_product_ids)

    # Priority 1: Same category as items in cart
    if cart_category_ids:
        cat_qs = base_qs.filter(category_id__in=cart_category_ids)
        recommended = list(cat_qs.select_related('category')[:6])

    # Priority 2: Same brand
    if len(recommended) < 6 and cart_brands:
        existing_ids = [p.id for p in recommended]
        brand_products = list(
            base_qs.filter(brand__in=cart_brands)
            .exclude(id__in=existing_ids)
            .select_related('category')[:6 - len(recommended)]
        )
        recommended.extend(brand_products)

    # Priority 3: Newest products
    if len(recommended) < 6:
        existing_ids = [p.id for p in recommended]
        newest = list(
            base_qs.exclude(id__in=existing_ids)
            .order_by('-created_at')
            .select_related('category')[:6 - len(recommended)]
        )
        recommended.extend(newest)

    # Priority 4: Random fallback
    if len(recommended) < 6:
        existing_ids = [p.id for p in recommended]
        random_count = 6 - len(recommended)
        random_ids = list(
            base_qs.exclude(id__in=existing_ids)
            .order_by('?')[:random_count]
            .values_list('id', flat=True)
        )
        if random_ids:
            random_products = list(
                Product.objects.filter(id__in=random_ids).select_related('category')
            )
            recommended.extend(random_products)

    return render(request, 'cart.html', {
        'cart': cart,
        'items': items,
        'total': total,
        'currency': currency,
        'payment_settings': payment_settings,
        'checkout_available': checkout_available,
        'checkout_notice': checkout_notice,
        'recommended_products': recommended,
        'free_shipping_threshold': free_shipping_threshold,
        'free_shipping_remaining': free_shipping_remaining,
        'free_shipping_percent': free_shipping_percent,
        'savings': 0,
    })


@login_required
def add_to_cart(request, product_id):
    """
    Add product to cart with validation.
    
    ✅ FIX: Handle GET requests gracefully (redirect instead of 405)
    ✅ FIX #2: Size validation against ProductSize model
    ✅ OPTIMIZATION: Invalidate session cache after adding
    """
    if request.method != 'POST':
        return redirect('products:shop')
    
    product = get_object_or_404(Product, id=product_id)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
    size = request.POST.get('size', '').strip().upper()
    
    has_sizes = product.sizes.exists()
    
    if has_sizes and not size:
        return JsonResponse({'success': False, 'error': 'Please select a size'}, status=400)
    
    # 🔧 FIX #2: Validate size exists in ProductSize model
    if has_sizes and size:
        size_exists = product.sizes.filter(size=size).exists()
        if not size_exists:
            return JsonResponse({'success': False, 'error': f'Invalid size: {size}'}, status=400)
    
    if quantity <= 0:
        return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
    
    available_stock = product.stock
    if size:
        try:
            product_size = product.sizes.get(size=size)
            available_stock = product_size.stock
        except ProductSize.DoesNotExist:
            pass
    
    if available_stock < quantity:
        return JsonResponse({'success': False, 'error': 'Not enough stock'}, status=400)
    
    cart = Cart.get_for_user(request.user)
    
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        size=size,
        defaults={'quantity': quantity}
    )
    
    message = f'{product.name} added to cart'
    
    if not created:
        new_quantity = cart_item.quantity + quantity
        check_stock = product.stock
        if cart_item.size:
            try:
                product_size = product.sizes.get(size=cart_item.size)
                check_stock = product_size.stock
            except ProductSize.DoesNotExist:
                pass
        if check_stock < new_quantity:
            return JsonResponse({'success': False, 'error': 'Not enough stock'}, status=400)
        cart_item.quantity = new_quantity
        cart_item.save()
        message = f'{product.name} quantity updated'
    
    cart_count = cart.items.count()
    
    # 🚀 OPTIMIZATION: Invalidate cart count cache in session
    session_key = f'cart_count_{request.user.id}'
    if session_key in request.session:
        del request.session[session_key]
    
    return JsonResponse({
        'success': True,
        'message': message,
        'cart_count': cart_count,
        'is_updated': not created
    })


@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart and invalidate cache."""
    if request.method not in ('POST', 'DELETE'):
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    cart = Cart.get_for_user(request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    
    cart_count = cart.items.count()
    cart_total = cart.total
    
    # 🚀 OPTIMIZATION: Invalidate cart count cache
    session_key = f'cart_count_{request.user.id}'
    if session_key in request.session:
        del request.session[session_key]
    
    return JsonResponse({
        'success': True,
        'message': 'Item removed from cart',
        'cart_count': cart_count,
        'cart_total': float(cart_total)
    })


@login_required
def update_cart_item(request, item_id):
    """Update cart item quantity and invalidate cache."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    cart = Cart.get_for_user(request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)

    if quantity <= 0:
        cart_item.delete()
        cart_count = cart.items.count()
        cart_total = cart.total if cart.items.exists() else 0
        
        # 🚀 OPTIMIZATION: Invalidate cache
        session_key = f'cart_count_{request.user.id}'
        if session_key in request.session:
            del request.session[session_key]
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'cart_count': cart_count,
            'cart_total': float(cart_total),
            'item_removed': True
        })

    check_stock = cart_item.product.stock
    if cart_item.size:
        try:
            product_size = cart_item.product.sizes.get(size=cart_item.size)
            check_stock = product_size.stock
        except ProductSize.DoesNotExist:
            pass

    if check_stock < quantity:
        return JsonResponse({'success': False, 'error': 'Not enough stock'}, status=400)

    cart_item.quantity = quantity
    cart_item.save()

    cart_count = cart.items.count()
    cart_total = cart.total
    
    # 🚀 OPTIMIZATION: Invalidate cache on update
    session_key = f'cart_count_{request.user.id}'
    if session_key in request.session:
        del request.session[session_key]

    return JsonResponse({
        'success': True,
        'message': 'Cart updated',
        'cart_count': cart_count,
        'cart_total': float(cart_total),
        'item_subtotal': float(cart_item.subtotal)
    })
