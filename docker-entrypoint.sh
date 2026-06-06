#!/bin/sh
set -e
# RUN_CELERY is set only on the Railway "worker" service, so web/Meridian keep
# serving the API alone. The worker runs the Celery consumer in the background
# and uvicorn in the foreground (same image, so the platform healthcheck on
# /health keeps passing).
if [ "$RUN_CELERY" = "1" ]; then
  celery -A src.workers.celery_app:celery_app worker \
    --loglevel="${CELERY_LOG_LEVEL:-info}" \
    -Q "${CELERY_QUEUES:-critical,default,analysis,reports,sync}" \
    --concurrency="${CELERY_CONCURRENCY:-2}" \
    --max-tasks-per-child=200 &
fi
exec uvicorn src.api.app:app --host 0.0.0.0 --port "${PORT:-8000}"
