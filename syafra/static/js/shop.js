/* ============================================
   SYAFRA Shop — Frontend Interactions
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {

    const grid = document.getElementById('product-grid');
    const gridBtns = document.querySelectorAll('.shop-topbar__grid-btn');
    const sortSelect = document.getElementById('shop-sort');
    const filterForm = document.getElementById('shop-filter-form');
    const resetBtn = document.getElementById('shop-filter-reset');
    const accordionHeaders = document.querySelectorAll('.shop-filters__header');
    const colorBtns = document.querySelectorAll('.shop-filters__color');
    const pricePresets = document.querySelectorAll('.shop-filters__price-preset');
    const brandChecks = document.querySelectorAll('.shop-filter-brand');

    /* ---- Grid Toggle ---- */
    if (grid && gridBtns.length) {
        gridBtns.forEach(function (btn) {
            btn.addEventListener('click', function () {
                var cols = this.getAttribute('data-col');
                gridBtns.forEach(function (b) { b.classList.remove('is-active'); });
                this.classList.add('is-active');
                grid.className = 'product-grid product-grid--' + cols;
                localStorage.setItem('shopGridCols', cols);
            });
        });

        var savedCols = localStorage.getItem('shopGridCols') || '4';
        var activeBtn = document.querySelector('.shop-topbar__grid-btn[data-col="' + savedCols + '"]');
        if (activeBtn) {
            gridBtns.forEach(function (b) { b.classList.remove('is-active'); });
            activeBtn.classList.add('is-active');
            grid.className = 'product-grid product-grid--' + savedCols;
        }
    }

    /* ---- Sort ---- */
    if (sortSelect && grid) {
        sortSelect.addEventListener('change', function () {
            var cards = Array.from(grid.querySelectorAll('.product-card'));
            var order = this.value;

            cards.sort(function (a, b) {
                var valA, valB;
                switch (order) {
                    case 'price-asc':
                        valA = parseFloat(a.getAttribute('data-price'));
                        valB = parseFloat(b.getAttribute('data-price'));
                        return valA - valB;
                    case 'price-desc':
                        valA = parseFloat(a.getAttribute('data-price'));
                        valB = parseFloat(b.getAttribute('data-price'));
                        return valB - valA;
                    case 'alpha':
                        valA = a.getAttribute('data-name').toLowerCase();
                        valB = b.getAttribute('data-name').toLowerCase();
                        return valA.localeCompare(valB);
                    default:
                        return 0;
                }
            });

            var fragment = document.createDocumentFragment();
            cards.forEach(function (card) { fragment.appendChild(card); });
            grid.appendChild(fragment);
        });
    }

    /* ---- Accordion Filters ---- */
    accordionHeaders.forEach(function (header) {
        var group = header.closest('.shop-filters__group');

        header.addEventListener('click', function () {
            var isOpen = group.classList.contains('is-open');
            group.classList.toggle('is-open');
            header.setAttribute('aria-expanded', !isOpen);
        });
    });

    /* ---- Color Filter (visual only) ---- */
    colorBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            colorBtns.forEach(function (b) { b.classList.remove('is-active'); });
            this.classList.add('is-active');
        });
    });

    /* ---- Price Presets ---- */
    pricePresets.forEach(function (btn) {
        btn.addEventListener('click', function () {
            pricePresets.forEach(function (b) { b.classList.remove('is-active'); });
            this.classList.add('is-active');
            var min = this.getAttribute('data-min');
            var max = this.getAttribute('data-max');
            filterByPrice(min, max);
        });
    });

    function filterByPrice(min, max) {
        if (!grid) return;
        var cards = grid.querySelectorAll('.product-card');
        cards.forEach(function (card) {
            var price = parseFloat(card.getAttribute('data-price'));
            var show = true;
            if (min !== '' && price < parseFloat(min)) show = false;
            if (max !== '' && price > parseFloat(max)) show = false;
            card.style.display = show ? '' : 'none';
        });
    }

    /* ---- Brand Filter (populated from products) ---- */
    var brandContainer = document.getElementById('shop-filter-brands');
    if (brandContainer && grid) {
        var brandSet = {};
        var cards = grid.querySelectorAll('.product-card');
        cards.forEach(function (card) {
            var brand = card.getAttribute('data-brand');
            if (brand) brandSet[brand] = true;
        });
        var brands = Object.keys(brandSet).sort();
        if (brands.length) {
            brandContainer.innerHTML = '';
            brands.forEach(function (brand) {
                var label = document.createElement('label');
                label.className = 'shop-filters__item';
                label.innerHTML = '<input type="checkbox" name="brand" value="' + brand.replace(/"/g, '&quot;') + '" class="shop-filter-brand">'
                    + '<span class="shop-filters__check"></span>'
                    + '<span class="shop-filters__label">' + brand + '</span>';
                brandContainer.appendChild(label);
            });

            brandChecks = brandContainer.querySelectorAll('.shop-filter-brand');
            brandChecks.forEach(function (cb) {
                cb.addEventListener('change', function () {
                    filterByBrand();
                });
            });
        }
    }

    function filterByBrand() {
        if (!grid) return;
        var checked = [];
        brandChecks.forEach(function (cb) {
            if (cb.checked) checked.push(cb.value);
        });
        var allCards = grid.querySelectorAll('.product-card');
        allCards.forEach(function (card) {
            var brand = card.getAttribute('data-brand');
            card.style.display = (!checked.length || checked.indexOf(brand) !== -1) ? '' : 'none';
        });
    }

    /* ---- Auto-submit on backend filter change ---- */
    var autoSubmitInputs = filterForm ? filterForm.querySelectorAll('input[name="category"], input[name="size"], input[name="stock"]') : [];
    autoSubmitInputs.forEach(function (input) {
        input.addEventListener('change', function () {
            filterForm.submit();
        });
    });

    /* ---- Reset Filters ---- */
    if (resetBtn) {
        resetBtn.addEventListener('click', function () {
            window.location.href = resetBtn.closest('form').action;
        });
    }

    /* ---- Product Card Click (handled by quickview.js modal) ---- */
    var productCards = document.querySelectorAll('.product-card');
    productCards.forEach(function (card) {
        card.addEventListener('click', function (e) {
            if (e.target.closest('.product-card__quickview')) return;
            var href = this.getAttribute('data-href');
            if (href) window.location.href = href;
        });
    });

});
