"""
Optional Celery monitoring with Flower.

Add to requirements.txt:
    flower>=2.0.0

Run locally:
    celery -A syafra flower

Production:
    - Add 'flower' dyno/process on Heroku/Railway
    - Command: celery -A syafra flower --port=$PORT
    - Require authentication to prevent exposing internal tasks
"""

import os
from django.conf import settings

# Flower web interface configuration
FLOWER_PORT = int(os.getenv('FLOWER_PORT', 5555))
FLOWER_BASIC_AUTH = os.getenv('FLOWER_BASIC_AUTH', '')  # user:password
FLOWER_BROKER_API_TIMEOUT = 10

# Optional: Email alerts on task failures (set up if needed)
FLOWER_ENABLE_EMAIL_ALERTS = os.getenv('FLOWER_ENABLE_EMAIL_ALERTS', 'false').lower() in ('1', 'true')
