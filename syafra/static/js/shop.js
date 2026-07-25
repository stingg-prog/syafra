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

    /* ---- Form submit: disable inactive section to prevent duplicate params ---- */
    form.addEventListener('submit', function (e) {
        disableInactiveSection();
    });

    /* ---- Disable inactive section inputs to prevent duplicate params ---- */
    function disableInactiveSection() {
        var isDesktop = window.innerWidth >= 1024;
        var filterbar = document.getElementById('shop-filterbar');
        var drawerEl = document.getElementById('shop-drawer');
        var sections = filterbar ? [filterbar] : [];
        if (drawerEl) sections.push(drawerEl);
        sections.forEach(function (section) {
            section.querySelectorAll('input, select, button, textarea').forEach(function (el) {
                el.disabled = false;
            });
        });
        var target = isDesktop ? drawerEl : filterbar;
        if (target) {
            target.querySelectorAll('input, select, button, textarea').forEach(function (el) {
                el.disabled = true;
            });
        }
    }

    function submitForm() {
        disableInactiveSection();
        form.submit();
    }

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

    document.addEventListener('click', function (e) {
        if (!e.target.closest('.shop-filterbar__price') && !e.target.closest('.shop-filterbar__dropdown')) {
            closeAllDropdowns();
        }
    });

    /* ---- Auto-submit on Desktop Filter Change ---- */
    var autoSubmitSelectors = [
        '.shop-filterbar__dropdown input[type="radio"]',
        '.shop-filterbar__dropdown input[type="checkbox"]',
    ];

    autoSubmitSelectors.forEach(function (selector) {
        form.querySelectorAll(selector).forEach(function (input) {
            input.addEventListener('change', function () {
                if (window.innerWidth >= 1024) {
                    submitForm();
                }
            });
        });
    });

    /* ---- Price Range: Manual Apply / Clear / Validation ---- */
    function getPriceDropdown() {
        return document.querySelector('.shop-filterbar__dropdown[data-dropdown="price"]');
    }

    function closePriceDropdown() {
        var dd = getPriceDropdown();
        if (dd && dd.classList.contains('is-open')) {
            dd.classList.remove('is-open');
            dd.querySelector('.shop-filterbar__dropdown-btn').setAttribute('aria-expanded', 'false');
        }
    }

    function getPriceValues() {
        var min = document.getElementById('price-min');
        var max = document.getElementById('price-max');
        var minMobile = document.getElementById('price-min-mobile');
        var maxMobile = document.getElementById('price-max-mobile');
        return {
            min: min,
            max: max,
            minMobile: minMobile,
            maxMobile: maxMobile,
            minVal: min ? min.value.trim() : '',
            maxVal: max ? max.value.trim() : '',
        };
    }

    function showPriceError(msg) {
        var elDesktop = document.getElementById('price-error-desktop');
        var elMobile = document.getElementById('price-error-mobile');
        if (elDesktop) elDesktop.textContent = msg;
        if (elMobile) elMobile.textContent = msg;
    }

    function submitPriceFilter() {
        var pv = getPriceValues();
        var minVal = pv.minVal;
        var maxVal = pv.maxVal;

        if (!minVal && !maxVal) return;

        if (minVal && maxVal && parseFloat(minVal) > parseFloat(maxVal)) {
            showPriceError('Minimum price cannot exceed maximum price.');
            return;
        }

        showPriceError('');
        submitForm();
    }

    function clearPriceFilter(e) {
        if (e) e.stopPropagation();
        var pv = getPriceValues();
        if (pv.min) pv.min.value = '';
        if (pv.max) pv.max.value = '';
        if (pv.minMobile) pv.minMobile.value = '';
        if (pv.maxMobile) pv.maxMobile.value = '';
        showPriceError('');
        submitForm();
    }

    function syncMobilePriceToDesktop() {
        var pv = getPriceValues();
        if (pv.min && pv.minMobile) pv.min.value = pv.minMobile.value;
        if (pv.max && pv.maxMobile) pv.max.value = pv.maxMobile.value;
    }

    function syncDesktopPriceToMobile() {
        var pv = getPriceValues();
        if (pv.min && pv.minMobile) pv.minMobile.value = pv.min.value;
        if (pv.max && pv.maxMobile) pv.maxMobile.value = pv.max.value;
    }

    /* Apply button */
    var applyDesktop = document.getElementById('price-apply-desktop');
    var applyMobile = document.getElementById('price-apply-mobile');
    if (applyDesktop) {
        applyDesktop.addEventListener('click', function (e) {
            e.stopPropagation();
            submitPriceFilter();
            closePriceDropdown();
        });
    }
    if (applyMobile) {
        applyMobile.addEventListener('click', function (e) {
            e.stopPropagation();
            syncMobilePriceToDesktop();
            submitPriceFilter();
        });
    }

    /* Clear button */
    var clearDesktop = document.getElementById('price-clear-desktop');
    var clearMobile = document.getElementById('price-clear-mobile');
    if (clearDesktop) {
        clearDesktop.addEventListener('click', function (e) {
            e.stopPropagation();
            clearPriceFilter();
        });
    }
    if (clearMobile) {
        clearMobile.addEventListener('click', function (e) {
            e.stopPropagation();
            syncMobilePriceToDesktop();
            clearPriceFilter();
        });
    }

    /* Enter key on price inputs */
    function handlePriceEnter(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            var isDesktop = window.innerWidth >= 1024;
            if (isDesktop) {
                submitPriceFilter();
                closePriceDropdown();
            } else {
                syncMobilePriceToDesktop();
                submitPriceFilter();
            }
        }
    }

    var priceInputIds = ['price-min', 'price-max', 'price-min-mobile', 'price-max-mobile'];
    priceInputIds.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) {
            el.addEventListener('keydown', handlePriceEnter);
        }
    });

    /* Escape key closes desktop price dropdown */
    function handlePriceEscape(e) {
        if (e.key === 'Escape') {
            var dd = getPriceDropdown();
            if (dd && dd.classList.contains('is-open')) {
                e.stopPropagation();
                closePriceDropdown();
                dd.querySelector('.shop-filterbar__dropdown-btn').focus();
            }
        }
    }

    priceInputIds.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) {
            el.addEventListener('keydown', handlePriceEscape);
        }
    });

    /* Clear validation error on input */
    function clearPriceError() {
        showPriceError('');
    }

    ['price-min', 'price-max', 'price-min-mobile', 'price-max-mobile'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', clearPriceError);
        }
    });

    /* ---- Sort Sync (desktop ↔ mobile) ---- */
    function syncSort(source, target) {
        if (!source || !target) return;
        source.addEventListener('change', function () {
            target.value = this.value;
            submitForm();
        });
        target.addEventListener('change', function () {
            source.value = this.value;
            submitForm();
        });
    }

    if (sortSelect && sortSelectMobile) {
        sortSelectMobile.value = sortSelect.value;
        syncSort(sortSelect, sortSelectMobile);
    }

    /* ---- Mobile Drawer ---- */
    function closeDrawer() {
        if (!drawer || !drawerOverlay) return;
        drawer.classList.remove('is-open');
        drawerOverlay.classList.remove('is-visible');
        document.body.style.overflow = '';
    }

    if (drawerOpen && drawer && drawerOverlay && drawerClose) {
        drawerOpen.addEventListener('click', function () {
            drawer.classList.add('is-open');
            drawerOverlay.classList.add('is-visible');
            document.body.style.overflow = 'hidden';
        });

        drawerClose.addEventListener('click', closeDrawer);
        drawerOverlay.addEventListener('click', closeDrawer);
    }

    /* ---- Drawer close on Escape ---- */
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && drawer && drawer.classList.contains('is-open')) {
            closeDrawer();
            if (drawerOpen) drawerOpen.focus();
        }
    });

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
            var existing = form.querySelector('input[name="search"]');
            if (existing) existing.remove();
            searchInput.name = 'q';
            submitForm();
        }

        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitSearch();
            }
        });
    }

});
