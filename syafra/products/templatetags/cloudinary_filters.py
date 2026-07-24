from django import template


register = template.Library()


def _cloudinary_transform(url, transformation):
    if not url:
        return ""

    url = str(url)
    marker = "/upload/"

    if marker not in url:
        return url

    suffix = url.split(marker, 1)[1]
    if suffix.startswith(f"{transformation}/"):
        return url

    return url.replace(marker, f"{marker}{transformation}/", 1)


@register.filter
def cloudinary_normalize(url):
    return _cloudinary_transform(
        url,
        "w_600,h_800,c_pad,b_white,f_auto,q_auto",
    )


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    request = context.get('request')
    if not request:
        return ''
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value == '':
            params.pop(key, None)
        else:
            params[key] = str(value)
    return params.urlencode()

@register.simple_tag(takes_context=True)
def url_remove(context, *keys):
    request = context.get('request')
    if not request:
        return ''
    params = request.GET.copy()
    for key in keys:
        params.pop(key, None)
    return params.urlencode()

@register.filter
def get_by_key(d, key):
    if isinstance(d, dict):
        return d.get(key)
    return None


@register.simple_tag(takes_context=True)
def render_section_attrs(context, section):
    from django.utils.html import format_html, mark_safe
    attrs = []
    if section.anchor_id:
        attrs.append(f'id="{section.anchor_id}"')
    classes = ['section-wrapper']
    if section.border_radius:
        classes.append(section.border_radius)
    if section.custom_css_class:
        classes.append(section.custom_css_class)
    if section.animation:
        attrs.append(f'data-aos="{section.animation}"')
    if section.hide_on_mobile:
        classes.append('hide-mobile')
    if section.hide_on_tablet:
        classes.append('hide-tablet')
    if section.hide_on_desktop:
        classes.append('hide-desktop')
    styles = []
    if section.bg_color:
        styles.append(f'background-color:{section.bg_color}')
    if section.margin:
        margin_map = {'m-0': '0', 'mt-4': '1rem 0 0 0', 'mt-8': '2rem 0 0 0', 'mt-16': '4rem 0 0 0',
                      'mb-4': '0 0 1rem 0', 'mb-8': '0 0 2rem 0', 'mb-16': '0 0 4rem 0',
                      'my-4': '1rem 0', 'my-8': '2rem 0', 'my-16': '4rem 0'}
        margin_css = margin_map.get(section.margin)
        if margin_css:
            styles.append(f'margin:{margin_css}')
    if styles:
        attrs.append(f'style="{"; ".join(styles)}"')
    if classes:
        attrs.append(f'class="{" ".join(classes)}"')
    return mark_safe(' '.join(attrs))


@register.filter
def split(value, delimiter=','):
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter) if item.strip()]


@register.filter
def get_by_index(lst, index):
    try:
        if index < 0:
            return None
        return lst[index]
    except (IndexError, TypeError, ValueError):
        return None


@register.filter
def cloudinary_resize(url, size="600x800"):
    if not url:
        return ""

    try:
        width, height = [part.strip() for part in str(size).lower().split("x", 1)]
        if not width or not height:
            return str(url)
    except ValueError:
        return str(url)

    return _cloudinary_transform(
        url,
        f"w_{width},h_{height},c_pad,b_white,f_auto,q_auto",
    )
