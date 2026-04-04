"""
SYAFRA Django project package.
"""

try:
    from .celery import app as celery_app
except ImportError:  # pragma: no cover - Celery remains optional in local/test envs.
    celery_app = None

__all__ = ('celery_app',)
