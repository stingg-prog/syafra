/* ============================================
   SYAFRA Shop — Premium Collection Interactions
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {

    var form = document.getElementById('shop-filter-form');
    if (!form) return;

    var sortSelect = document.getElementById('shop-sort');
    var sortSelectMobile = document.getElementById('shop-sort-mobile');
    var searchInput = document.getElementById('shop-search-input');
    var drawerOpen = document.getElementById('shop-drawer-open');
    var drawerClose = document.getElementById('shop-drawer-close');
    var drawerOverlay = document.getElementById('shop-drawer-overlay');
    var drawer = document.getElementById('shop-drawer');
    var dropdownBtns = document.querySelectorAll('.shop-filterbar__dropdown-btn');
    var drawerGroupHeaders = document.querySelectorAll('.shop-drawer__group-header');
    var productCards = document.querySelectorAll('.product-card');

    /* ---- Desktop Dropdowns ---- */
    dropdownBtns.forEach(function (btn) {
        var dropdown = btn.closest('.shop-filterbar__dropdown');

        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            var isOpen = dropdown.classList.contains('is-open');

            closeAllDropdowns();

            if (!isOpen) {
                dropdown.classList.add('is-open');
                btn.setAttribute('aria-expanded', 'true');
            }
        });
    });

    function closeAllDropdowns() {
        document.querySelectorAll('.shop-filterbar__dropdown.is-open').forEach(function (d) {
            d.classList.remove('is-open');
            d.querySelector('.shop-filterbar__dropdown-btn').setAttribute('aria-expanded', 'false');
        });
    }

    document.addEventListener('click', function () {
        closeAllDropdowns();
    });

    /* ---- Auto-submit on Desktop Filter Change ---- */
    var autoSubmitSelectors = [
        '.shop-filterbar__dropdown input[type="radio"]',
        '.shop-filterbar__dropdown input[type="checkbox"]',
        '.shop-filterbar__dropdown input[type="number"]',
    ];

    autoSubmitSelectors.forEach(function (selector) {
        form.querySelectorAll(selector).forEach(function (input) {
            input.addEventListener('change', function () {
                if (window.innerWidth >= 1025) {
                    form.submit();
                }
            });
        });
    });

    var priceInputs = form.querySelectorAll('.shop-filterbar__dropdown input[type="number"]');
    priceInputs.forEach(function (input) {
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && window.innerWidth >= 1025) {
                form.submit();
            }
        });
    });

    /* ---- Sort Sync (desktop ↔ mobile) ---- */
    function syncSort(source, target) {
        if (!source || !target) return;
        source.addEventListener('change', function () {
            target.value = this.value;
            form.submit();
        });
        target.addEventListener('change', function () {
            source.value = this.value;
            form.submit();
        });
    }

    if (sortSelect && sortSelectMobile) {
        sortSelectMobile.value = sortSelect.value;
        syncSort(sortSelect, sortSelectMobile);
    }

    /* ---- Mobile Drawer ---- */
    if (drawerOpen && drawer && drawerOverlay && drawerClose) {
        drawerOpen.addEventListener('click', function () {
            drawer.classList.add('is-open');
            drawerOverlay.classList.add('is-visible');
            document.body.style.overflow = 'hidden';
        });

        function closeDrawer() {
            drawer.classList.remove('is-open');
            drawerOverlay.classList.remove('is-visible');
            document.body.style.overflow = '';
        }

        drawerClose.addEventListener('click', closeDrawer);
        drawerOverlay.addEventListener('click', closeDrawer);
    }

    /* ---- Drawer Accordion ---- */
    drawerGroupHeaders.forEach(function (header) {
        var group = header.closest('.shop-drawer__group');

        header.addEventListener('click', function () {
            var isOpen = group.classList.contains('is-open');
            group.classList.toggle('is-open');
            header.setAttribute('aria-expanded', !isOpen);
        });
    });

    /* ---- Search ---- */
    if (searchInput) {
        function submitSearch() {
            var hidden = form.querySelector('input[name="search"]');
            if (!hidden) {
                hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = 'search';
                form.appendChild(hidden);
            }
            hidden.value = searchInput.value;
            form.submit();
        }

        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitSearch();
            }
        });
    }

    /* ---- Product Card Click ---- */
    productCards.forEach(function (card) {
        card.addEventListener('click', function (e) {
            if (e.target.closest('.product-card__quickview')) return;
            var url = this.getAttribute('data-product-url');
            if (url) window.location.href = url;
        });
    });

});
