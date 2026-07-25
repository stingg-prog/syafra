from django import template
from django.utils.safestring import mark_safe
from syafra.utils import sanitize_html

register = template.Library()


@register.filter
def sanitize(html):
    return mark_safe(sanitize_html(html))
