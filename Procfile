web: gunicorn stackOverflow:app --log-file= -
worker: celery worker --app=stackOverflow.app --loglevel=info
