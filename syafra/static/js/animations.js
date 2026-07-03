/**
 * Animations - Scroll reveal, navbar scroll effect, smooth anchor scrolling
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        // Scroll reveal (IntersectionObserver)
        var revealElements = document.querySelectorAll('.reveal');
        if (revealElements.length > 0) {
            var revealObserver = new IntersectionObserver(
                function (entries) {
                    entries.forEach(function (entry) {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('revealed');
                        }
                    });
                },
                {
                    threshold: 0.1,
                    rootMargin: '0px 0px -50px 0px',
                }
            );

            revealElements.forEach(function (el) {
                revealObserver.observe(el);
            });
        }

        // Navbar scroll effect
        var navbar = document.querySelector('nav');
        if (navbar) {
            var scrollHandler = function () {
                var currentScroll = window.pageYOffset;
                if (currentScroll > 50) {
                    navbar.classList.add('nav-scrolled');
                } else {
                    navbar.classList.remove('nav-scrolled');
                }
            };

            window.addEventListener('scroll', scrollHandler, { passive: true });
            // Apply on load in case page is already scrolled
            scrollHandler();
        }

        // Smooth scroll for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
            anchor.addEventListener('click', function (e) {
                var href = this.getAttribute('href');
                if (href === '#' || href.length < 2) return;
                var target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    });
})();
