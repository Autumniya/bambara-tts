#!/bin/bash
# Start Celery in background
celery -A celery_worker.celery_app worker --loglevel=info &
# Start Gunicorn
exec gunicorn app:app --bind 0.0.0.0:8080 --timeout 120
