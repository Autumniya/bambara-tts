web: celery -A celery_worker.celery_app worker --loglevel=info & gunicorn app:app --bind 0.0.0.0:8080 --timeout 120
