web: gunicorn stackOverflow:app
worker: celery -A stackOverflow.celery_instance worker --loglevel=info --concurrency=1



