"""
Middleware for request-scoped correlation ids.
"""
import re
from uuid import uuid4

from .logging_context import reset_correlation_id, set_correlation_id

_MAX_CORRELATION_ID_LENGTH = 64
_VALID_CORRELATION_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def _is_valid_correlation_id(value: str) -> bool:
    if len(value) > _MAX_CORRELATION_ID_LENGTH:
        return False
    try:
        from uuid import UUID
        UUID(value)
        return True
    except ValueError:
        pass
    return bool(_VALID_CORRELATION_ID_RE.match(value))


class RequestCorrelationIdMiddleware:
    header_names = ('HTTP_X_REQUEST_ID', 'HTTP_X_CORRELATION_ID')
    response_header = 'X-Request-ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = ''
        for header_name in self.header_names:
            correlation_id = (request.META.get(header_name) or '').strip()
            if correlation_id:
                break
        if not correlation_id or not _is_valid_correlation_id(correlation_id):
            correlation_id = uuid4().hex

        request.correlation_id = correlation_id
        request.META['HTTP_X_REQUEST_ID'] = correlation_id
        token = set_correlation_id(correlation_id)
        try:
            response = self.get_response(request)
        finally:
            reset_correlation_id(token)

        response[self.response_header] = correlation_id
        return response
