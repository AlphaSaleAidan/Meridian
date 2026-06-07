#!/bin/sh
set -e
# RUN_CELERY is set only on the Railway "worker" service, so web/Meridian keep
# serving the API alone. On the worker we must load the heavy ML app exactly
# ONCE (it OOMs the instance otherwise), so we run Celery with --pool=solo (no
# prefork children = one app copy) and answer the platform /health probe from a
# tiny stdlib HTTP server that imports nothing from the app.
if [ "$RUN_CELERY" = "1" ]; then
  python -c "
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type','application/json')
        self.end_headers(); self.wfile.write(b'{\"status\":\"healthy\",\"role\":\"worker\"}')
    def log_message(self, *a): pass
ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', 8000))), H).serve_forever()
" &
  # --beat embeds the scheduler in this single worker so the periodic tasks in
  # celery_app.beat_schedule (billing renewals, daily burn rate, nightly
  # analysis, weekly reports, etc.) actually enqueue. Embedded (not a separate
  # process) keeps the one-app-copy / OOM-safe invariant. Schedule db goes to
  # /tmp because /app is not writable by appuser.
  exec celery -A src.workers.celery_app:celery_app worker \
    --pool=solo \
    --beat \
    --schedule=/tmp/celerybeat-schedule \
    --loglevel="${CELERY_LOG_LEVEL:-info}" \
    -Q "${CELERY_QUEUES:-critical,default,bulk}"
fi
exec uvicorn src.api.app:app --host 0.0.0.0 --port "${PORT:-8000}"
