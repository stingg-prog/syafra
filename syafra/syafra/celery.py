"""
Celery application bootstrap.
Only used when CELERY_TASK_ALWAYS_EAGER=False (i.e., real async workers deployed).
"""
import os

if os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'true').lower() == 'false':
    from celery import Celery
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')
    app = Celery('syafra')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()
else:
    app = None
