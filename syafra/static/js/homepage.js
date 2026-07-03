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

    window.submitNewsletter = function (e) {
        e.preventDefault();
        var form = document.getElementById('newsletter-form');
        var msg = document.getElementById('newsletter-message');
        if (!form || !msg) return false;

        var formData = new FormData(form);
        var csrfToken =
            document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        msg.classList.remove('newsletter-success-anim');

        fetch(form.getAttribute('action') || window.location.href, {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': csrfToken },
        })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                msg.classList.remove('hidden', 'is-success', 'is-error');
                if (data.success) {
                    msg.classList.add('is-success', 'newsletter-success-anim');
                    form.reset();
                } else {
                    msg.classList.add('is-error');
                }
                msg.textContent = data.message || data.error;
            })
            .catch(function () {
                msg.classList.remove('hidden', 'is-success', 'is-error');
                msg.classList.add('is-error');
                msg.textContent =
                    'Something went wrong. Please try again.';
            });

        return false;
    };

    // Expose getCookie globally for cart/checkout scripts that need it
    window.getCookie = getCookie;
})();
