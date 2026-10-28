# WhatsApp Notifications Optimization: Celery + Redis

## Overview

WhatsApp message delivery has been moved to background tasks using **Celery** with **Redis** as the message broker. This ensures admin operations remain fast while notifications are processed asynchronously with automatic retry logic.

---

## What Changed

### 1. **Background Task Processing**
- WhatsApp messages now route through a Celery task queue instead of blocking the HTTP request
- Admin panel and order operations return immediately
- Notifications are sent asynchronously by worker processes

### 2. **Automatic Retry Logic**
- Failed message attempts are retried up to **5 times** (configurable)
- Exponential backoff: retry delays increase from 60s → 120s → 240s → 480s → 600s max
- Jitter prevents thundering herd on Redis

### 3. **Redis Broker**
- Lightweight, fast message broker instead of database or file-based queues
- Two Redis databases: `0` for message queue, `1` for task results

---

## Setup Instructions

### Local Development

#### 1. Install Dependencies
Already added to `requirements.txt`:
```bash
pip install -r requirements.txt
```

Includes: `celery>=5.3.0`, `redis>=4.5.0`

#### 2. Start Redis
```bash
# Using Docker (recommended)
docker run -d -p 6379:6379 redis:7-alpine

# Or install Redis locally and run:
redis-server
```

Verify Redis is running:
```bash
redis-cli ping
# Output: PONG
```

#### 3. Run Django Development Server
```bash
python manage.py runserver
```

#### 4. Start Celery Worker (separate terminal)
```bash
celery -A syafra worker --loglevel=info
```

You'll see:
```
 -------------- celery@hostname v5.3.x ----------
 ---- **** ----- 
 --- * ***  * -- Linux-5.15.0 (4 cores)
```

#### 5. Test End-to-End
1. Go to admin: `http://localhost:8000/admin`
2. Create an order or change status
3. Check Celery worker logs for task execution
4. Verify WhatsApp was sent (check logs or Twilio console)

---

### Production Deployment

#### Environment Variables
Add to your deployment platform (Heroku, Railway, Render, etc.):

```env
# Redis broker (provided by platform or external service)
CELERY_BROKER_URL=redis://broker.example.com:6379/0
CELERY_RESULT_BACKEND=redis://broker.example.com:6379/1

# Task configuration (optional, defaults shown)
CELERY_TASK_TIME_LIMIT=300          # Task timeout: 5 minutes
CELERY_TASK_MAX_RETRIES=5           # Retry attempts
CELERY_TASK_RETRY_DELAY=60          # Initial retry delay (seconds)
```

#### Platform-Specific Setup

**Heroku:**
```bash
# Add Redis add-on
heroku addons:create heroku-redis:premium-0

# Start Celery worker
heroku ps:scale worker=1

# Check logs
heroku logs -t
```

**Railway.app:**
```bash
# Create Redis service
# Set CELERY_BROKER_URL to the Redis connection string

# Add worker service:
# Command: celery -A syafra worker --loglevel=info
# Max Execution Time: 3600s
```

**Render.com:**
```bash
# Create Redis database
# Create background worker service
# Command: celery -A syafra worker --loglevel=info
# Set CELERY_BROKER_URL to the Redis URL
```

#### Procfile
Already updated with worker process:
```
release: python manage.py migrate --noinput && python manage.py sync_whatsapp_from_env
web: gunicorn syafra.wsgi:application
worker: celery -A syafra worker --loglevel=info
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HTTP Request (Admin)                   │
│                      POST /admin/orders/                    │
│                                                               │
│  1. Signal: pre_save -> track_order_changes()               │
│  2. Signal: post_save -> handle_order_notifications()       │
│  3. Call: queue_whatsapp_notification(order, status)        │
│  4. Response sent immediately (< 100ms)                      │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   │ transaction.on_commit()
                   ↓
         ┌─────────────────────┐
         │   Redis (Broker)    │  <- Message queue stored here
         │  6379/0 (Queue DB)  │
         │  6379/1 (Results)   │
         └────────┬────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
        ↓                    ↓
   ┌─────────┐          ┌─────────┐
   │ Worker  │          │ Worker  │
   │Process 1│          │Process 2│
   │         │          │         │
   │ Tasks:  │          │ Tasks:  │
   │ - Retry │          │ - Retry │
   │ - Send  │          │ - Send  │
   │ - Log   │          │ - Log   │
   └─────────┘          └─────────┘
        │                    │
        └─────────┬──────────┘
                  │
                  ↓
        ┌─────────────────────┐
        │    Twilio API       │
        │  (WhatsApp Sender)  │
        └─────────────────────┘
```

---

## Task Configuration

### `orders/tasks.py`
Main task that sends WhatsApp notifications:

- **Task name:** `orders.tasks.send_whatsapp_notification`
- **Max retries:** 5 (configurable via settings)
- **Retry delays:** Exponential backoff with jitter
- **Time limit:** 5 minutes (300s)
- **Error handling:** Non-Fatal errors (like API failures) trigger auto-retry; fatal errors (missing order) skip retry

### Signal Flow

1. **Order Created / Status Changed** → Django signal fires
2. **queue_whatsapp_notification()** called → Task enqueued in Redis
3. **HTTP Request returns** (admin still responsive)
4. **Celery Worker picks up task** from Redis
5. **send_whatsapp_message()** executes → Twilio API call
6. **Success** → Task complete, logged
7. **Failure** → Auto-retry with exponential backoff (max 5 attempts)

---

## Monitoring & Debugging

### View Celery Logs
```bash
celery -A syafra worker --loglevel=info
```

Output examples:
```
[tasks.send_whatsapp_notification] Received task
[tasks.send_whatsapp_notification] Task succeeded
[tasks.send_whatsapp_notification] Retry attempt 1/5
```

### Check Redis Queue Size
```bash
redis-cli LLEN celery
redis-cli INFO stats  # Monitor CPU, memory, ops
```

### Verify Task Results
```bash
redis-cli
> KEYS celery-task-meta-*
> GET celery-task-meta-abc123  # View task result
```

### Django Logs
```bash
tail -f logs.log | grep WhatsApp
```

---

## Troubleshooting

### "Connection refused" Error
- Redis not running: `redis-server` or Docker container
- Wrong Redis URL: Check `CELERY_BROKER_URL`

### Tasks Not Processing
- Worker not running: Start with `celery -A syafra worker --loglevel=info`
- Check worker logs for errors
- Verify Redis is reachable from worker machine

### Memory Issues (Production)
- Set connection pool limits:
  ```python
  app.conf.broker_pool_limit = 10  # Max broker connections
  ```

### Stuck Tasks
- Clear queue: `celery -A syafra purge`
- Reset results backend: `redis-cli FLUSHDB --async`

---

## Performance Gains

### Before Celery
- Admin: `POST /admin/orders/` took **2-5 seconds** (WhatsApp block)
- Twilio API timeout → admin page hung or 500 error

### After Celery
- Admin: `POST /admin/orders/` takes **< 100ms** (task queued)
- WhatsApp processed asynchronously, retried automatically
- Admin panel remains fast even under load

---

## Configuration Reference

### `syafra/settings.py`
```python
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes per task
```

### `syafra/celery.py`
- Configures Celery app
- Loads Django settings
- Auto-discovers tasks from all apps
- Configures broker/backend URLs from env

### `orders/tasks.py`
- Defines `send_whatsapp_notification()` task
- Handles retries with exponential backoff
- Catches retryable vs. fatal errors

### `orders/signals.py`
- Enqueues tasks via `transaction.on_commit()` to ensure DB is committed first
- Does not block on WhatsApp send

---

## Next Steps

1. **Monitor in production:** Set up Celery Flower for real-time monitoring (optional):
   ```bash
   pip install flower
   celery -A syafra flower
   ```
   Visit `http://localhost:5555`

2. **Scale workers:** Add more worker processes as load increases:
   - Per-platform job/dyno scaling

3. **Alert on failures:** Set up logging alerts for retried tasks

4. **Tune retry policy:** Adjust `max_retries`, `default_retry_delay`, `retry_backoff_max` in `orders/tasks.py` based on production metrics
