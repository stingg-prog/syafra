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
