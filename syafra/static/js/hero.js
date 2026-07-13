/**
 * Hero - Slideshow, Ken Burns, numbered dots, prev/next arrows, parallax
 */
(function () {
    'use strict';

    var SLIDESHOW_INTERVAL = 6000;

    document.addEventListener('DOMContentLoaded', function () {
        var hero = document.getElementById('hero');
        if (!hero) return;

        var slides = hero.querySelectorAll('.hero-slide');
        var dots = hero.querySelectorAll('.hero-dot');
        var scrollIndicator = document.getElementById('hero-scroll-indicator');
        var prevBtn = hero.querySelector('.hero-arrow-prev');
        var nextBtn = hero.querySelector('.hero-arrow-next');
        var currentSlideEl = hero.querySelector('.hero-current-slide');

        // ---- Hero Content Animation on Entry ----
        if (slides.length > 0) {
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        hero.classList.add('is-active');
                    }
                });
            }, { threshold: 0.1 });

            observer.observe(hero);
        }

        // ---- Parallax Effect (applied to wrapper so it doesn't conflict with Ken Burns) ----
        var heroImageWrapper = hero.querySelector('.hero-image-wrapper');
        if (heroImageWrapper) {
            var parallaxHandler = function () {
                var scrolled = window.pageYOffset;
                if (scrolled < hero.offsetHeight) {
                    var translateY = scrolled * 0.12;
                    heroImageWrapper.style.transform = 'translateY(' + translateY + 'px)';
                }
            };

            window.addEventListener('scroll', parallaxHandler, { passive: true });
        }

        // ---- Scroll Indicator Hide ----
        if (scrollIndicator) {
            var hideScroll = function () {
                if (window.pageYOffset > 100) {
                    scrollIndicator.classList.add('hidden');
                } else {
                    scrollIndicator.classList.remove('hidden');
                }
            };
            window.addEventListener('scroll', hideScroll, { passive: true });
        }

        // ---- Slideshow ----
        if (slides.length <= 1) return;

        var current = 0;
        var intervalId;
        var isTransitioning = false;

        function updateCounter(index) {
            if (currentSlideEl) {
                var num = (index + 1).toString();
                currentSlideEl.textContent = num.length < 2 ? '0' + num : num;
            }
        }

        function showSlide(index) {
            if (isTransitioning || index === current) return;
            isTransitioning = true;

            var currentSlide = slides[current];
            var nextSlide = slides[index];

            currentSlide.classList.remove('is-active');
            var currentImg = currentSlide.querySelector('.hero-image');
            if (currentImg) currentImg.classList.remove('ken-burns');

            nextSlide.classList.add('is-active');
            var nextImg = nextSlide.querySelector('.hero-image');
            if (nextImg) nextImg.classList.add('ken-burns');

            // Update dots
            dots.forEach(function (d) {
                d.classList.remove('is-active');
                d.setAttribute('aria-selected', 'false');
            });
            dots[index].classList.add('is-active');
            dots[index].setAttribute('aria-selected', 'true');

            // Update counter
            updateCounter(index);

            current = index;

            setTimeout(function () {
                isTransitioning = false;
            }, 800);
        }

        function nextSlide() {
            showSlide((current + 1) % slides.length);
        }

        function prevSlide() {
            showSlide((current - 1 + slides.length) % slides.length);
        }

        // Dot click handlers
        dots.forEach(function (dot) {
            dot.addEventListener('click', function () {
                var index = parseInt(this.dataset.index);
                if (index !== current) {
                    showSlide(index);
                    clearInterval(intervalId);
                    intervalId = setInterval(nextSlide, SLIDESHOW_INTERVAL);
                }
            });
        });

        // Arrow click handlers
        if (prevBtn) {
            prevBtn.addEventListener('click', function () {
                prevSlide();
                clearInterval(intervalId);
                intervalId = setInterval(nextSlide, SLIDESHOW_INTERVAL);
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', function () {
                nextSlide();
                clearInterval(intervalId);
                intervalId = setInterval(nextSlide, SLIDESHOW_INTERVAL);
            });
        }

        // Auto-advance
        intervalId = setInterval(nextSlide, SLIDESHOW_INTERVAL);

        // Pause when hidden
        document.addEventListener('visibilitychange', function () {
            if (document.hidden) {
                clearInterval(intervalId);
            } else {
                intervalId = setInterval(nextSlide, SLIDESHOW_INTERVAL);
            }
        });
    });
})();
