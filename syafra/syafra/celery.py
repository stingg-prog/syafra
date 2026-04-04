"""
Celery application bootstrap.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')

app = Celery('syafra')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    return {
        'request_id': getattr(self.request, 'id', None),
        'delivery_info': getattr(self.request, 'delivery_info', None),
    }
