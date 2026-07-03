/**
 * Quick View Modal - Product preview with details
 */
(function () {
    'use strict';

    var modal = null;
    var isOpen = false;

    function createModal() {
        if (modal) return;
        modal = document.createElement('div');
        modal.className = 'quickview-modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-label', 'Quick View');
        modal.innerHTML =
            '<div class="quickview-modal__backdrop"></div>' +
            '<div class="quickview-modal__container">' +
                '<button class="quickview-modal__close" aria-label="Close">' +
                    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">' +
                        '<path d="M18 6L6 18M6 6l12 12"/>' +
                    '</svg>' +
                '</button>' +
                '<div class="quickview-modal__body">' +
                    '<div class="quickview-modal__image"></div>' +
                    '<div class="quickview-modal__details">' +
                        '<div class="quickview-modal__brand"></div>' +
                        '<div class="quickview-modal__name"></div>' +
                        '<div class="quickview-modal__price"></div>' +
                        '<div class="quickview-modal__condition"></div>' +
                        '<div class="quickview-modal__sizes"></div>' +
                        '<a class="quickview-modal__cta" href="#">View Full Details</a>' +
                    '</div>' +
                '</div>' +
            '</div>';
        document.body.appendChild(modal);

        // Close handlers
        modal.querySelector('.quickview-modal__backdrop').addEventListener('click', close);
        modal.querySelector('.quickview-modal__close').addEventListener('click', close);
        document.addEventListener('keydown', function (e) {
            if (isOpen && e.key === 'Escape') close();
        });
    }

    function open(card) {
        createModal();
        var productUrl = card.getAttribute('data-product-url') || '#';
        var img = card.querySelector('.product-card__image img');
        var brand = card.querySelector('.product-card__brand');
        var name = card.querySelector('.product-card__name');
        var price = card.querySelector('.product-card__price-current');
        var condition = card.querySelector('.product-card__badges .badge');
        var sizes = card.querySelectorAll('.product-card__size-dot');

        modal.querySelector('.quickview-modal__image').innerHTML =
            img ? '<img src="' + img.src + '" alt="' + (img.alt || '') + '">' : '';
        modal.querySelector('.quickview-modal__brand').textContent = brand ? brand.textContent : '';
        modal.querySelector('.quickview-modal__name').textContent = name ? name.textContent : '';
        modal.querySelector('.quickview-modal__price').textContent = price ? price.textContent : '';
        modal.querySelector('.quickview-modal__condition').innerHTML =
            condition ? '<span class="badge ' + condition.className + '">' + condition.textContent + '</span>' : '';

        var sizesHtml = '';
        if (sizes.length) {
            sizesHtml = '<div class="quickview-modal__size-dots">';
            sizes.forEach(function (s) {
                sizesHtml += '<span class="product-card__size-dot">' + s.textContent + '</span>';
            });
            sizesHtml += '</div>';
        }
        modal.querySelector('.quickview-modal__sizes').innerHTML = sizesHtml;
        modal.querySelector('.quickview-modal__cta').href = productUrl;

        modal.classList.add('is-open');
        isOpen = true;
        document.body.style.overflow = 'hidden';
    }

    function close() {
        if (!modal) return;
        modal.classList.remove('is-open');
        isOpen = false;
        document.body.style.overflow = '';
    }

    function init() {
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('.product-card__quickview');
            if (!btn) return;
            e.preventDefault();
            e.stopPropagation();
            var card = btn.closest('.product-card');
            if (card) open(card);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.SyafraQuickView = { open: open, close: close };
})();
