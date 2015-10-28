web: gunicorn stackOverflow:app
worker: celery -A stackOverflow.celery worker --loglevel=info --concurrency=1



