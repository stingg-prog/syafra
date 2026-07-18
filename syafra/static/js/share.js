var ShareSheet = (function () {
    'use strict';

    var sheet, panel, backdrop, closeBtn, options;
    var shareBtn;
    var isOpen = false;
    var isMobile = window.innerWidth < 768;
    var productData = {};

    var PLATFORM_CONFIG = {
        whatsapp: buildWhatsApp,
        instagram: shareInstagram,
        facebook: shareFacebook,
        twitter: shareTwitter,
        telegram: shareTelegram,
        email: shareEmail,
        copy: copyLink,
    };

    function getProductUrl() {
        return productData.url || window.location.href;
    }

    function getShareText() {
        return productData.shareText || productData.title + '\n' + getProductUrl();
    }

    function getProductTitle() {
        return productData.title || '';
    }

    function init(config) {
        productData = {
            title: config.title || document.title,
            url: config.url || window.location.href,
            price: config.price || '',
            shareText: config.shareText || '',
        };

        sheet = document.getElementById('share-sheet');
        if (!sheet) return;

        panel = sheet.querySelector('.share-sheet__panel');
        backdrop = sheet.querySelector('.share-sheet__backdrop');
        closeBtn = sheet.querySelector('.share-sheet__close');
        options = sheet.querySelectorAll('[data-share]');
        shareBtn = document.getElementById('share-action-btn');

        bindEvents();
        handleResize();
        detectViewport();
    }

    function detectViewport() {
        isMobile = window.innerWidth < 768;
        if (!sheet) return;
        sheet.classList.toggle('share-sheet--dropdown', !isMobile);
    }

    function bindEvents() {
        if (shareBtn) {
            shareBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                handleShareTrigger();
            });
        }

        if (backdrop) {
            backdrop.addEventListener('click', close);
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', close);
        }

        options.forEach(function (opt) {
            opt.addEventListener('click', function (e) {
                var platform = opt.getAttribute('data-share');
                handlePlatformShare(platform);
            });
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && isOpen) {
                close();
                if (shareBtn) shareBtn.focus();
            }
        });

        window.addEventListener('resize', handleResize);
    }

    function handleResize() {
        var wasMobile = isMobile;
        detectViewport();
        if (isOpen && wasMobile !== isMobile) {
            if (!isMobile) {
                positionDropdown();
            }
        }
    }

    function handleShareTrigger() {
        if (navigator.share) {
            navigator.share({
                title: getProductTitle(),
                text: getShareText(),
                url: getProductUrl(),
            })
            .then(function () {})
            .catch(function (err) {
                if (err.name !== 'AbortError') {
                    openCustomSheet();
                }
            });
        } else {
            openCustomSheet();
        }
    }

    function openCustomSheet() {
        if (isOpen) return;
        isOpen = true;

        sheet.removeAttribute('hidden');
        requestAnimationFrame(function () {
            sheet.classList.add('is-open');
        });
        document.body.classList.add('share-sheet-open');

        if (!isMobile) {
            positionDropdown();
        }

        focusFirst();
    }

    function positionDropdown() {
        if (!shareBtn || !panel) return;

        var btnRect = shareBtn.getBoundingClientRect();
        var panelWidth = 320;
        var gap = 10;
        var panelHeight = Math.min(420, panel.scrollHeight || 420);

        var left = Math.max(16, Math.min(
            btnRect.left + btnRect.width / 2 - panelWidth / 2,
            window.innerWidth - panelWidth - 16
        ));

        var spaceBelow = window.innerHeight - btnRect.bottom;
        var spaceAbove = btnRect.top;
        var top;

        if (spaceBelow >= panelHeight + gap + 16) {
            top = btnRect.bottom + gap;
            panel.style.transformOrigin = 'top center';
        } else if (spaceAbove >= panelHeight + gap + 16) {
            top = btnRect.top - gap - panelHeight;
            panel.style.transformOrigin = 'bottom center';
        } else {
            top = Math.max(16, (window.innerHeight - panelHeight) / 2);
            panel.style.transformOrigin = 'center center';
        }

        panel.style.left = left + 'px';
        panel.style.top = top + 'px';
        panel.style.width = panelWidth + 'px';

        var arrow = sheet.querySelector('.share-sheet__arrow');
        if (arrow) {
            var arrowLeft = btnRect.left + btnRect.width / 2 - left - 7;
            arrow.style.left = Math.max(8, Math.min(arrowLeft, panelWidth - 22)) + 'px';
            if (spaceBelow >= panelHeight + gap + 16) {
                arrow.style.top = '-7px';
            } else if (spaceAbove >= panelHeight + gap + 16) {
                arrow.style.bottom = '-7px';
                arrow.style.top = 'auto';
            } else {
                arrow.style.display = 'none';
            }
        }
    }

    function close() {
        if (!isOpen) return;
        isOpen = false;

        sheet.classList.remove('is-open');
        document.body.classList.remove('share-sheet-open');

        setTimeout(function () {
            sheet.setAttribute('hidden', '');
            if (panel) {
                panel.style.left = '';
                panel.style.top = '';
                panel.style.width = '';
            }
        }, 350);
    }

    function focusFirst() {
        if (closeBtn) {
            setTimeout(function () { closeBtn.focus(); }, 50);
        }
    }

    function handlePlatformShare(platform) {
        var fn = PLATFORM_CONFIG[platform];
        if (fn) fn();
    }

    function buildWhatsApp() {
        var text = getShareText();
        var url = isMobile
            ? 'https://api.whatsapp.com/send?text=' + encodeURIComponent(text)
            : 'https://web.whatsapp.com/send?text=' + encodeURIComponent(text);
        openUrl(url);
        close();
    }

    function shareInstagram() {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(getProductUrl()).catch(function () {});
        }
        window.showToast('Link copied! Open Instagram to share.', 'success', 3000);

        var instagramAppUrl = 'instagram://';
        var instagramWebUrl = 'https://www.instagram.com/';

        var opened = false;
        try {
            var w = window.open(instagramAppUrl, '_blank');
            if (w) {
                opened = true;
                setTimeout(function () { w.close(); }, 500);
            }
        } catch (e) {}

        if (!opened) {
            window.open(instagramWebUrl, '_blank', 'noopener,noreferrer');
        }
        close();
    }

    function shareFacebook() {
        var url = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(getProductUrl());
        openUrl(url);
        close();
    }

    function shareTwitter() {
        var text = getShareText();
        var url = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(text);
        openUrl(url);
        close();
    }

    function shareTelegram() {
        var text = getShareText();
        var url = 'https://t.me/share/url?url=' + encodeURIComponent(getProductUrl()) + '&text=' + encodeURIComponent(text);
        openUrl(url);
        close();
    }

    function shareEmail() {
        var subject = 'Check out ' + getProductTitle() + ' on SYAFRA';
        var body = getShareText();
        var url = 'mailto:?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
        openUrl(url);
        close();
    }

    function copyLink() {
        var textToCopy = getShareText();
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(textToCopy).then(function () {
                window.showToast('Link copied successfully.', 'success');
            }).catch(function () {
                fallbackCopy(textToCopy);
            });
        } else {
            fallbackCopy(textToCopy);
        }
        close();
    }

    function fallbackCopy(text) {
        var textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        textarea.style.pointerEvents = 'none';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            window.showToast('Link copied successfully.', 'success');
        } catch (e) {
            window.showToast('Unable to copy link.', 'error');
        }
        document.body.removeChild(textarea);
    }

    function openUrl(url) {
        window.open(url, '_blank', 'noopener,noreferrer');
    }

    return {
        init: init,
        open: function () { handleShareTrigger(); },
        close: close,
    };
})();
