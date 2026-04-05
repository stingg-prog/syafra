"""
SYAFRA Django project package.
"""

try:
    from syafra.celery import app as celery_app
except Exception:
    celery_app = None

__all__ = ('celery_app',)
