/**
 * Navbar - Glass morphism, mobile drawer, announcement dismiss
 */
(function () {
    'use strict';

    var SCROLL_THRESHOLD = 50;
    var STORAGE_KEY = 'syafra_announcement_dismissed';

    /* ---- Announcement Bar Dismiss ---- */
    function initAnnouncement() {
        var bar = document.querySelector('.announcement-bar');
        var closeBtn = document.querySelector('.announcement-close');
        if (!bar || !closeBtn) return;

        // Check localStorage
        if (localStorage.getItem(STORAGE_KEY) === '1') {
            bar.classList.add('is-dismissed');
            updateNavPosition(true);
            return;
        }

        closeBtn.addEventListener('click', function () {
            bar.classList.add('is-dismissed');
            localStorage.setItem(STORAGE_KEY, '1');
            updateNavPosition(true);
        });
    }

    function updateNavPosition(dismissed) {
        var nav = document.querySelector('.site-nav');
        if (!nav) return;
        if (dismissed) {
            nav.classList.remove('has-announcement');
        } else {
            nav.classList.add('has-announcement');
        }
    }

    /* ---- Glass Morphism on Scroll ---- */
    function initScrollEffect() {
        var nav = document.querySelector('.site-nav');
        if (!nav) return;

        var scrolled = false;

        function onScroll() {
            var currentScroll = window.pageYOffset;
            if (currentScroll > SCROLL_THRESHOLD && !scrolled) {
                nav.classList.add('nav--scrolled');
                scrolled = true;
            } else if (currentScroll <= SCROLL_THRESHOLD && scrolled) {
                nav.classList.remove('nav--scrolled');
                scrolled = false;
            }
        }

        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll(); // apply on load
    }

    /* ---- Mobile Menu ---- */
    function initMobileMenu() {
        var btn = document.getElementById('mobile-menu-btn');
        var menu = document.getElementById('mobile-menu');
        if (!btn || !menu) return;

        function openMenu() {
            menu.classList.add('is-open');
            btn.setAttribute('aria-expanded', 'true');
            document.body.classList.add('menu-open');
        }

        function closeMenu() {
            menu.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
            document.body.classList.remove('menu-open');
        }

        function toggleMenu() {
            if (menu.classList.contains('is-open')) {
                closeMenu();
            } else {
                openMenu();
            }
        }

        btn.addEventListener('click', toggleMenu);

        // Close on link click
        menu.querySelectorAll('.nav-link').forEach(function (link) {
            link.addEventListener('click', closeMenu);
        });

        // Close on outside click
        document.addEventListener('click', function (e) {
            if (menu.classList.contains('is-open') && !menu.contains(e.target) && !btn.contains(e.target)) {
                closeMenu();
            }
        });

        // Close on Escape
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && menu.classList.contains('is-open')) {
                closeMenu();
            }
        });
    }

    /* ---- Init ---- */
    document.addEventListener('DOMContentLoaded', function () {
        var nav = document.querySelector('.site-nav');
        var bar = document.querySelector('.announcement-bar');

        // Check if announcement is dismissed
        if (bar && localStorage.getItem(STORAGE_KEY) === '1') {
            bar.classList.add('is-dismissed');
            updateNavPosition(true);
        } else if (bar) {
            updateNavPosition(false);
        }

        initAnnouncement();
        initScrollEffect();
        initMobileMenu();
    });
})();
