from django import template
from django.contrib.admin.models import LogEntry

register = template.Library()


@register.simple_tag
def get_unique_admin_log(user, limit=8):
    """Show the latest action per object without deleting audit history."""
    entries = (
        LogEntry.objects.filter(user=user)
        .select_related("content_type")
        .order_by("-action_time")[: max(limit * 5, 40)]
    )
    result = []
    seen = set()
    for entry in entries:
        key = (entry.content_type_id, entry.object_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)
        if len(result) >= limit:
            break
    return result
