/**
 * Wishlist - Heart animation + localStorage persistence
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'syafra_wishlist';

    function getWishlist() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
        } catch (e) {
            return [];
        }
    }

    function saveWishlist(ids) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    }

    function toggleWishlist(productId) {
        var ids = getWishlist();
        var idx = ids.indexOf(productId);
        if (idx === -1) {
            ids.push(productId);
        } else {
            ids.splice(idx, 1);
        }
        saveWishlist(ids);
        return idx === -1;
    }

    function isWishlisted(productId) {
        return getWishlist().indexOf(productId) !== -1;
    }

    function updateButton(btn, active) {
        if (active) {
            btn.classList.add('is-active');
        } else {
            btn.classList.remove('is-active');
        }
    }

    function init() {
        var buttons = document.querySelectorAll('.product-card__wishlist');
        buttons.forEach(function (btn) {
            var card = btn.closest('.product-card');
            if (!card) return;
            var productId = card.getAttribute('data-product-id');
            if (!productId) return;

            // Set initial state
            updateButton(btn, isWishlisted(productId));

            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var nowActive = toggleWishlist(productId);
                updateButton(btn, nowActive);
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.SyafraWishlist = { toggle: toggleWishlist, isWishlisted: isWishlisted };
})();
