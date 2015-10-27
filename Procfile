web: gunicorn stackOverflow:app --log-file=-
worker: celery worker -A stackOverflow.celery --loglevel=info
