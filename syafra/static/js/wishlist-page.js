(function () {
    'use strict';

    var grid = document.getElementById('wishlist-grid');
    var sortSelect = document.getElementById('wishlist-sort');
    var toastContainer = null;

    function ensureToastContainer() {
        if (toastContainer) return;
        toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none';
            document.body.appendChild(toastContainer);
        }
    }

    function showToast(message, type) {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type || 'success');
            return;
        }
        ensureToastContainer();
        type = type || 'info';
        var toast = document.createElement('div');
        toast.className = 'max-w-sm w-full rounded-xl border shadow-lg px-4 py-3 text-sm font-medium transition-all duration-300 transform opacity-0 translate-y-4';
        var colors = { success: 'bg-emerald-50 border-emerald-200 text-emerald-800', error: 'bg-rose-50 border-rose-200 text-rose-800', info: 'bg-sky-50 border-sky-200 text-sky-800' };
        toast.className += ' ' + (colors[type] || colors.info);
        toast.textContent = message;
        toastContainer.appendChild(toast);
        requestAnimationFrame(function () {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        });
        var hide = function () {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(16px)';
            setTimeout(function () { toast.remove(); }, 300);
        };
        toast.addEventListener('click', hide);
        setTimeout(hide, 4000);
    }

    /* ---- Sort ---- */
    if (sortSelect) {
        sortSelect.addEventListener('change', function () {
            var params = new URLSearchParams(window.location.search);
            params.set('sort', this.value);
            params.delete('page');
            window.location.search = params.toString();
        });
    }

    /* ---- Card Remove Animation ---- */
    document.addEventListener('wishlist:toggle', function (e) {
        if (!grid) return;
        var detail = e.detail;
        if (!detail || detail.wishlisted) return;

        var card = grid.querySelector(
            '.wishlist-card[data-product-id="' + detail.productId + '"]'
        );
        if (!card) return;

        card.classList.add('is-removing');
        setTimeout(function () {
            card.classList.add('is-removed');
            showToast('Removed from Wishlist', 'info');
            var remaining = grid.querySelectorAll('.wishlist-card:not(.is-removed)').length;
            if (remaining === 0) {
                setTimeout(function () {
                    window.location.reload();
                }, 400);
            }
        }, 250);
    });

    /* ---- Move to Cart ---- */
    document.addEventListener('submit', function (e) {
        var form = e.target.closest('.wishlist-cart-form');
        if (!form) return;

        e.preventDefault();

        var action = form.getAttribute('action');
        if (!action) return;

        var formData = new FormData(form);
        var csrf = formData.get('csrfmiddlewaretoken') || '';

        showToast('Adding to cart\u2026', 'info');

        fetch(action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrf,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: new URLSearchParams(formData),
        })
            .then(function (res) {
                return res.json().then(function (data) {
                    if (!res.ok) throw new Error(data.error || 'Failed to add to cart');
                    return data;
                });
            })
            .then(function (data) {
                if (data.success) {
                    showToast('Added to cart', 'success');
                } else {
                    showToast(data.error || 'Unable to add to cart.', 'error');
                }
            })
            .catch(function (err) {
                showToast(err.message || 'Network error. Please try again.', 'error');
            });
    });
})();