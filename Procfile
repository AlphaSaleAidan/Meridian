web: uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}
worker: celery -A src.workers.celery_app worker --loglevel=info --concurrency=4 -Q default,sync,analysis,reports
beat: celery -A src.workers.celery_app beat --loglevel=info
