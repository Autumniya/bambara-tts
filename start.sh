#!/bin/bash
# Start Celery in background
celery -A app.celery worker --loglevel=info --concurrency=1 &
# Start Gunicorn
exec gunicorn app:app --workers=1 --threads=1
