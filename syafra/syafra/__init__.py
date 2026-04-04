"""
SYAFRA Django project package.
"""

# Celery is optional - only import if celery is installed
try:
    from celery import Celery
    from .celery import app as celery_app
except ImportError:
    celery_app = None

__all__ = ('celery_app',)
