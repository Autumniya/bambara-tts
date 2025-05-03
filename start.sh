#!/bin/bash
# Start Celery in background
celery -A app.celery worker --loglevel=info &
# Start Gunicorn
exec gunicorn app:app --bind 0.0.0.0:8080 --timeout 120
