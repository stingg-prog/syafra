import bleach

ALLOWED_TAGS = list(bleach.ALLOWED_TAGS) + [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'br', 'hr', 'pre', 'code',
    'img', 'picture', 'source',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
    'dl', 'dd', 'dt',
    'div', 'span', 'section', 'article', 'aside', 'nav', 'header', 'footer',
    'figure', 'figcaption',
    'details', 'summary',
]

ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES)
ALLOWED_ATTRIBUTES['*'] = [
    'class', 'id', 'title', 'role', 'aria-label', 'aria-hidden',
    'data-*', 'tabindex',
]
ALLOWED_ATTRIBUTES['a'] = ['href', 'title', 'target', 'rel']
ALLOWED_ATTRIBUTES['img'] = ['src', 'alt', 'width', 'height', 'loading', 'decoding', 'srcset', 'sizes']
ALLOWED_ATTRIBUTES['source'] = ['srcset', 'media', 'type', 'sizes']
ALLOWED_ATTRIBUTES['td'] = ['colspan', 'rowspan', 'headers']
ALLOWED_ATTRIBUTES['th'] = ['colspan', 'rowspan', 'scope', 'headers']


def sanitize_html(html_string):
    if not html_string:
        return html_string
    return bleach.clean(
        html_string,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )
