# src/workers/ — Celery Background Tasks

App config: `celery_app.py` (broker=Redis, 4 queues: default, sync, analysis, reports)
Tasks: `tasks.py` (all task definitions)
Async bridge: `run_async()` wraps async coroutines for sync Celery

## Beat schedule
- nightly-analysis (24h) — sync + analyze all active merchants
- weekly-reports (7d) — generate reports for all merchants
- swarm-training (6h) — train on latest agent outputs
- vector-ingestion (6h) — ingest scraped data into embeddings
- daily-burn-rate (24h) — SMS cost report to admin
- billing-renewals (24h) — process subscription renewals

## Adding a task
1. Define `@shared_task` in `tasks.py`
2. Add route in `celery_app.py` `task_routes`
3. Add to `beat_schedule` if periodic
