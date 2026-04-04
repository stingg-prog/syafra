"""
Shared correlation-id helpers for request and task logging.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import logging

_correlation_id = ContextVar('correlation_id', default='-')


def get_correlation_id():
    return _correlation_id.get()


def set_correlation_id(value):
    value = value or '-'
    return _correlation_id.set(value)


def reset_correlation_id(token):
    _correlation_id.reset(token)


@contextmanager
def correlation_id_context(correlation_id):
    token = set_correlation_id(correlation_id or get_correlation_id())
    try:
        yield
    finally:
        reset_correlation_id(token)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = get_correlation_id()
        return True
