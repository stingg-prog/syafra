(function () {
    'use strict';

    var CONFIG = {
        loginUrl: window.SYAFRA_WISHLIST_LOGIN_URL || '/accounts/login/',
        isAuthenticated: window.SYAFRA_WISHLIST_AUTH === true,
        countUrl: '/wishlist/count/',
        addUrl: '/wishlist/add/',
        removeUrl: '/wishlist/remove/',
        statusUrl: '/wishlist/status/',
    };

    var navbarCount = null;
    var navbarCountValue = 0;

    function getCookie(name) {
        var value = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + '=') {
                    value = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return value;
    }

    function getCSRFToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.getAttribute('content');
        var input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) return input.value;
        return getCookie('csrftoken') || '';
    }

    function initNavbarCount() {
        var el = document.querySelector('.wishlist-nav-count');
        if (!el) return;
        navbarCount = el;
        navbarCountValue = parseInt(el.getAttribute('data-count') || '0', 10);
        updateNavbarDisplay();

        if (CONFIG.isAuthenticated) {
            fetch(CONFIG.countUrl, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success) {
                        navbarCountValue = data.count;
                        updateNavbarDisplay();
                    }
                })
                .catch(function () {});
        }
    }

    function updateNavbarDisplay() {
        if (!navbarCount) return;
        if (navbarCountValue > 0) {
            navbarCount.textContent = navbarCountValue;
            navbarCount.classList.remove('is-hidden');
        } else {
            navbarCount.classList.add('is-hidden');
        }
    }

    function bumpNavbarCount() {
        if (!navbarCount) return;
        navbarCount.classList.remove('is-bump');
        void navbarCount.offsetWidth;
        navbarCount.classList.add('is-bump');
    }

    function updateNavbarCount(delta) {
        navbarCountValue = Math.max(0, navbarCountValue + delta);
        updateNavbarDisplay();
        bumpNavbarCount();
    }

    function setNavbarCount(value) {
        navbarCountValue = value;
        updateNavbarDisplay();
    }

    function showToast(message, type) {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type || 'success');
        }
    }

    function redirectToLogin() {
        var currentPath = window.location.pathname + window.location.search;
        window.location.href = CONFIG.loginUrl + '?next=' + encodeURIComponent(currentPath);
    }

    function setHeartLoading(btn, loading) {
        if (!btn) return;
        if (loading) {
            btn.classList.add('is-loading');
        } else {
            btn.classList.remove('is-loading');
        }
    }

    function setHeartState(btn, wishlisted) {
        if (!btn) return;
        btn.classList.toggle('is-wishlisted', wishlisted);
        btn.setAttribute('aria-pressed', wishlisted ? 'true' : 'false');
        var label = wishlisted ? 'Remove from Wishlist' : 'Add to Wishlist';
        btn.setAttribute('aria-label', label);
    }

    function setPdpBtnState(btn, wishlisted) {
        if (!btn) return;
        btn.classList.toggle('is-wishlisted', wishlisted);
        var icon = btn.querySelector('.wishlist-btn__icon, .wishlist-pdp-btn__icon');
        if (icon) {
            icon.setAttribute('fill', wishlisted ? 'currentColor' : 'none');
        }
        var textSpan = btn.querySelector('.wishlist-pdp-btn__label');
        if (!textSpan) {
            textSpan = document.createElement('span');
            textSpan.className = 'wishlist-pdp-btn__label';
            btn.appendChild(textSpan);
        }
        textSpan.textContent = wishlisted ? 'WISHLISTED' : 'WISHLIST';
        btn.setAttribute('aria-pressed', wishlisted ? 'true' : 'false');
    }

    function handleWishlistToggle(btn, productId, isCurrentlyWishlisted) {
        if (!CONFIG.isAuthenticated) {
            redirectToLogin();
            return;
        }

        setHeartLoading(btn, true);

        var url = isCurrentlyWishlisted
            ? CONFIG.removeUrl + productId + '/'
            : CONFIG.addUrl + productId + '/';

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then(function (response) {
                if (response.status === 401 || response.status === 403) {
                    redirectToLogin();
                    return null;
                }
                if (response.status === 404) {
                    showToast('Product not found.', 'error');
                    return null;
                }
                return response.json();
            })
            .then(function (data) {
                if (!data) return;
                setHeartLoading(btn, false);
                if (data.success) {
                    var nowWishlisted = data.wishlisted;
                    var hearts = document.querySelectorAll(
                        '.wishlist-btn[data-product-id="' + productId + '"]'
                    );
                    for (var i = 0; i < hearts.length; i++) {
                        setHeartState(hearts[i], nowWishlisted);
                    }
                    var pdpBtns = document.querySelectorAll(
                        '.wishlist-pdp-btn[data-product-id="' + productId + '"]'
                    );
                    for (var j = 0; j < pdpBtns.length; j++) {
                        setPdpBtnState(pdpBtns[j], nowWishlisted);
                    }
                    if (typeof data.count !== 'undefined') {
                        setNavbarCount(data.count);
                    } else {
                        updateNavbarCount(nowWishlisted ? 1 : -1);
                    }
                    showToast(data.message, nowWishlisted ? 'success' : 'info');
                    try {
                        document.dispatchEvent(new CustomEvent('wishlist:toggle', {
                            detail: { productId: parseInt(productId), wishlisted: nowWishlisted }
                        }));
                    } catch (_) {}
                } else {
                    showToast(data.message || 'Unable to update wishlist.', 'error');
                }
            })
            .catch(function () {
                setHeartLoading(btn, false);
                showToast('Network error. Please try again.', 'error');
            });
    }

    function handleProductCardClick(e) {
        var btn = e.target.closest('.wishlist-btn');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();

        var productId = btn.getAttribute('data-product-id');
        if (!productId) return;

        var isWishlisted = btn.classList.contains('is-wishlisted');
        handleWishlistToggle(btn, productId, isWishlisted);
    }

    function handlePdpBtnClick(e) {
        var btn = e.target.closest('.wishlist-pdp-btn');
        if (!btn) return;
        e.preventDefault();

        var productId = btn.getAttribute('data-product-id');
        if (!productId) return;

        var isWishlisted = btn.classList.contains('is-wishlisted');
        handleWishlistToggle(btn, productId, isWishlisted);
    }

    function init() {
        initNavbarCount();

        document.addEventListener('click', handleProductCardClick);
        document.addEventListener('click', handlePdpBtnClick);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
