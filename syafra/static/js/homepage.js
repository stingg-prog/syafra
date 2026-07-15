/**
 * Homepage - Newsletter AJAX submission
 */
(function () {
    'use strict';

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + '=') {
                    cookieValue = decodeURIComponent(
                        cookie.substring(name.length + 1)
                    );
                    break;
                }
            }
        }
        return cookieValue;
    }

    var SUBSCRIBING_TEXT = 'Subscribing\u2026';

    function setLoading(form, input, btn, loading) {
        var btnText = btn.querySelector('.newsletter-btn__text');
        if (loading) {
            form.setAttribute('aria-busy', 'true');
            input.disabled = true;
            btn.disabled = true;
            btn.setAttribute('aria-disabled', 'true');
            btn.classList.add('is-loading');
            if (btnText) btnText.textContent = SUBSCRIBING_TEXT;
        } else {
            form.setAttribute('aria-busy', 'false');
            input.disabled = false;
            btn.disabled = false;
            btn.removeAttribute('aria-disabled');
            btn.classList.remove('is-loading');
            if (btnText) btnText.textContent = 'Subscribe';
        }
    }

    function resetForm(form, input, btn) {
        form.reset();
        setLoading(form, input, btn, false);
    }

    window.submitNewsletter = function (e) {
        e.preventDefault();
        var form = document.getElementById('newsletter-form');
        var msg = document.getElementById('newsletter-message');
        var input = document.getElementById('newsletter-email');
        var btn = document.getElementById('newsletter-submit');
        if (!form || !msg || !input || !btn) return false;

        var formData = new FormData(form);
        var csrfToken =
            document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        // Clear any pending auto-hide timeout
        if (form._newsletterTimeout) {
            clearTimeout(form._newsletterTimeout);
            form._newsletterTimeout = null;
        }

        msg.classList.remove('hidden', 'is-success', 'is-error', 'is-fading-out', 'newsletter-success-anim');
        msg.textContent = '';

        setLoading(form, input, btn, true);

        fetch(form.getAttribute('action') || window.location.href, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then(function (r) {
                if (!r.ok) {
                    return r.json().then(function (data) {
                        throw new Error(data.error || 'Request failed');
                    }, function () {
                        throw new Error('Server error (HTTP ' + r.status + ')');
                    });
                }
                return r.json();
            })
            .then(function (data) {
                if (data.success) {
                    msg.classList.add('is-success', 'newsletter-success-anim');
                    msg.textContent = data.message;

                    // After 2.5s: clear input, re-enable everything
                    form._newsletterTimeout = setTimeout(function () {
                        resetForm(form, input, btn);
                        // After another 1.5s (4s total): fade out message
                        form._newsletterTimeout = setTimeout(function () {
                            msg.classList.add('is-fading-out');
                            // After fade animation (300ms): hide fully
                            form._newsletterTimeout = setTimeout(function () {
                                msg.classList.add('hidden');
                                msg.classList.remove('is-success', 'is-fading-out');
                                msg.textContent = '';
                                form._newsletterTimeout = null;
                            }, 300);
                        }, 1500);
                    }, 2500);
                } else {
                    msg.classList.add('is-error');
                    msg.textContent = data.error || data.message || 'Please try again.';
                    setLoading(form, input, btn, false);
                }
            })
            .catch(function (err) {
                msg.classList.add('is-error');
                msg.textContent = err.message || 'Something went wrong. Please try again.';
                setLoading(form, input, btn, false);
            });

        return false;
    };

    // Expose getCookie globally for cart/checkout scripts that need it
    window.getCookie = getCookie;
})();
