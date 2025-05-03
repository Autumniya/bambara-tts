#!/bin/bash
# Start Celery in background
celery -A app.celery worker --loglevel=info &
# Start Gunicorn
exec gunicorn --workers=1 --preload app:app
