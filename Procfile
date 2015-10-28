web: gunicorn stackOverflow:app
worker: celery -A stack.celery worker --loglevel=info --concurrency=1
