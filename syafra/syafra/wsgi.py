"""
WSGI config for syafra project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from syafra.startup import repair_django_messages_module
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syafra.settings')
repair_django_messages_module()

application = get_wsgi_application()
