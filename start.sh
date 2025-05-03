#!/bin/bash
# Start Celery in background
celery -A app.celery worker --loglevel=info &
# Start Gunicorn
exec gunicorn --worker-class=gevent --worker-connections=1000 --workers=3 app:app
