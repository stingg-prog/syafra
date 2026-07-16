/* ============================================
   SYAFRA Product Detail — Frontend Interactions
   ============================================ */

var selectedSize = '';
var currentQty = 1;

/* ---- Gallery ---- */

function changeImage(thumbnail, imageUrl) {
    var mainImage = document.getElementById('mainImage');
    if (mainImage) mainImage.src = imageUrl;

    document.querySelectorAll('.pdp-gallery__thumb').forEach(function (thumb) {
        thumb.classList.remove('is-active');
    });
    thumbnail.classList.add('is-active');
}

/* ---- Size Selection ---- */

function selectSize(size) {
    selectedSize = size;
    document.querySelectorAll('.pdp-size__btn').forEach(function (btn) {
        btn.classList.remove('is-active');
    });
    var clickedBtn = document.querySelector('[data-size="' + size + '"]');
    if (clickedBtn) clickedBtn.classList.add('is-active');

    var display = document.getElementById('selected-size-display');
    if (display) display.textContent = size;

    var stockDisplay = document.getElementById('size-stock-display');
    if (!stockDisplay) return;
    var stock = clickedBtn ? clickedBtn.getAttribute('data-stock') : 0;
    if (stock == 0) {
        stockDisplay.textContent = 'Out of Stock';
        stockDisplay.className = 'pdp-size__stock pdp-size__stock--out';
    } else if (stock <= 3) {
        stockDisplay.textContent = 'Only ' + stock + ' left';
        stockDisplay.className = 'pdp-size__stock pdp-size__stock--low';
    } else {
        stockDisplay.textContent = stock + ' available';
        stockDisplay.className = 'pdp-size__stock pdp-size__stock--in';
    }
}

/* ---- Quantity ---- */

function incrementQty() {
    currentQty = Math.min(currentQty + 1, 10);
    updateQtyDisplay();
}

function decrementQty() {
    currentQty = Math.max(currentQty - 1, 1);
    updateQtyDisplay();
}

function updateQtyDisplay() {
    var el = document.getElementById('qty-value');
    if (el) el.textContent = currentQty;
}

/* ---- Accordion ---- */

function toggleAccordion(header) {
    var item = header.closest('.pdp-accordion__item');
    var isOpen = item.classList.contains('is-open');
    item.classList.toggle('is-open');
    header.setAttribute('aria-expanded', !isOpen);
}

/* ---- Add to Cart ---- */

function addToCart(productId) {
    var btn = document.getElementById('add-to-cart-btn');
    var sizeSelector = document.getElementById('size-selector');
    var hasSizes = sizeSelector && sizeSelector.querySelectorAll('.pdp-size__btn').length > 0;

    if (hasSizes && !selectedSize) {
        showToast('Please select a size.', 'error');
        return;
    }

    if (selectedSize) {
        var sizeBtn = document.querySelector('[data-size="' + selectedSize + '"]');
        if (sizeBtn && sizeBtn.disabled) {
            showToast('This size is out of stock.', 'error');
            return;
        }
    }

    btn.textContent = 'ADDING…';
    btn.disabled = true;

    var formData = new URLSearchParams();
    formData.append('quantity', currentQty.toString());
    if (selectedSize) formData.append('size', selectedSize);

    fetch('/cart/add/' + productId + '/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData.toString()
    })
    .then(function (response) {
        if (response.redirected) {
            window.location.href = response.url;
            return null;
        }
        return response.json();
    })
    .then(function (data) {
        if (!data) return;
        if (data.success) {
            btn.textContent = 'ADDED';
            btn.classList.add('is-added');

            var cartLink = document.querySelector('a[href*="cart"]');
            if (cartLink) {
                var badge = cartLink.querySelector('.cart-badge');
                if (!badge) {
                    badge = document.createElement('span');
                    badge.className = 'cart-badge';
                    cartLink.appendChild(badge);
                }
                badge.textContent = data.cart_count;
            }
            showToast('Added to bag.', 'success');

            setTimeout(function () {
                btn.textContent = 'ADD TO CART';
                btn.classList.remove('is-added');
                btn.disabled = false;
            }, 2000);
        } else {
            showToast(data.error || 'Unable to add item.', 'error');
            btn.textContent = 'ADD TO CART';
            btn.disabled = false;
        }
    })
    .catch(function () {
        showToast('Network error.', 'error');
        btn.textContent = 'ADD TO CART';
        btn.disabled = false;
    });
}

/* ---- From Wishlist Helper ---- */

(function handleFromWishlist() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('from') !== 'wishlist') return;

    var sizeSelector = document.getElementById('size-selector');
    if (!sizeSelector) return;

    var header = document.querySelector('.site-header');
    var headerHeight = header ? header.offsetHeight : 0;

    setTimeout(function () {
        var rect = sizeSelector.getBoundingClientRect();
        var scrollTarget = rect.top + window.pageYOffset - headerHeight - 20;
        window.scrollTo({ top: scrollTarget, behavior: 'smooth' });

        sizeSelector.classList.add('is-wishlist-highlight');

        var banner = document.createElement('div');
        banner.className = 'pdp-wishlist-banner';
        banner.innerHTML =
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>' +
            '<span>Select a size to add from your wishlist</span>' +
            '<button type="button" class="pdp-wishlist-banner__close" onclick="this.parentElement.remove()" aria-label="Dismiss">&times;</button>';

        var sizeSection = document.querySelector('.pdp-size');
        if (sizeSection) {
            sizeSection.parentNode.insertBefore(banner, sizeSection);
        }
    }, 400);
})();

/* ---- Buy Now ---- */

function buyNow(productId) {
    var btn = document.getElementById('add-to-cart-btn');
    var sizeSelector = document.getElementById('size-selector');
    var hasSizes = sizeSelector && sizeSelector.querySelectorAll('.pdp-size__btn').length > 0;

    if (hasSizes && !selectedSize) {
        showToast('Please select a size.', 'error');
        return;
    }

    if (selectedSize) {
        var sizeBtn = document.querySelector('[data-size="' + selectedSize + '"]');
        if (sizeBtn && sizeBtn.disabled) {
            showToast('This size is out of stock.', 'error');
            return;
        }
    }

    var formData = new URLSearchParams();
    formData.append('quantity', currentQty.toString());
    if (selectedSize) formData.append('size', selectedSize);

    fetch('/cart/add/' + productId + '/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData.toString()
    })
    .then(function (response) {
        if (response.redirected) {
            window.location.href = response.url;
            return null;
        }
        return response.json();
    })
    .then(function (data) {
        if (!data) return;
        if (data.success) {
            showToast('Added to bag. Redirecting…', 'success');
            setTimeout(function () {
                window.location.href = '/cart/';
            }, 500);
        } else {
            showToast(data.error || 'Unable to add item.', 'error');
        }
    })
    .catch(function () {
        showToast('Network error.', 'error');
    });
}
