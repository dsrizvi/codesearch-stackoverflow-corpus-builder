web: gunicorn stackOverflow:app
worker: celery -A --concurrency=1 stack.celery worker --loglevel=info
