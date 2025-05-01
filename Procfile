web: gunicorn app:app --bind 0.0.0.0:8080 --timeout 120
worker: celery -A celery_worker.celery_app worker --loglevel=info
