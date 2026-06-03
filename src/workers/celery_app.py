"""
Celery Application — Async task queue for Meridian.

Broker: Redis (configurable via REDIS_URL env var)
Backend: Redis (for result storage)

Tasks are defined in src/workers/tasks.py.
"""
import os

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "meridian",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_queues=[
        Queue('critical', routing_key='critical'),
        Queue('default', routing_key='default'),
        Queue('bulk', routing_key='bulk'),
    ],
    task_routes={
        "src.workers.tasks.sync_pos_data": {"queue": "default"},
        "src.workers.tasks.run_analysis": {"queue": "default"},
        "src.workers.tasks.process_billing_renewals": {"queue": "critical"},
        "src.workers.tasks.run_nightly_analysis": {"queue": "bulk"},
        "src.workers.tasks.run_nightly_analysis_complete": {"queue": "bulk"},
        "src.workers.tasks.generate_weekly_reports": {"queue": "bulk"},
        "src.workers.tasks.generate_report": {"queue": "default"},
        "src.workers.tasks.train_swarm": {"queue": "bulk"},
        "src.workers.tasks.train_swarm_batch": {"queue": "bulk"},
        "src.workers.tasks.run_cold_storage_archive": {"queue": "bulk"},
        "src.workers.tasks.archive_org_month": {"queue": "bulk"},
        "src.workers.tasks.upload_archive_to_r2": {"queue": "bulk"},
        "src.workers.tasks.offload_warm_to_r2": {"queue": "bulk"},
        "src.workers.tasks.ingest_scraped_data": {"queue": "bulk"},
        "src.workers.tasks.batch_local_inference": {"queue": "default"},
        "src.workers.tasks.rebuild_session_context": {"queue": "bulk"},
        "src.workers.tasks.rebuild_all_context": {"queue": "bulk"},
        "src.workers.tasks.rebuild_file_digest": {"queue": "bulk"},
        "src.workers.tasks.rebuild_diff_summaries": {"queue": "bulk"},
        "src.workers.tasks.compress_sessions": {"queue": "bulk"},
        "src.workers.tasks.send_daily_burn_rate": {"queue": "default"},
        # P3: POS pipeline on Celery
        "src.workers.tasks.backfill_pos_connection": {"queue": "bulk"},
        "src.workers.tasks.incremental_sync_all": {"queue": "default"},
        "src.workers.tasks.refresh_pos_tokens": {"queue": "default"},
    },
    result_expires=3600,
    worker_max_tasks_per_child=200,
    # Staggered to prevent simultaneous heavy/LLM tasks. Interval schedules
    # were converted to fixed crontabs so they don't align at beat-boot.
    # Minimum 90-min gap between any two LLM-heavy tasks.
    beat_schedule={
        "nightly-analysis": {
            "task": "src.workers.tasks.run_nightly_analysis",
            "schedule": crontab(hour=2, minute=0),  # 02:00 UTC daily
            "options": {"queue": "bulk"},
        },
        "weekly-reports": {
            "task": "src.workers.tasks.generate_weekly_reports",
            "schedule": crontab(hour=3, minute=15, day_of_week=1),  # Mon 03:15 UTC
            "options": {"queue": "bulk"},
        },
        "cold-storage-archive": {
            "task": "src.workers.tasks.run_cold_storage_archive",
            "schedule": crontab(hour=3, minute=30),  # 03:30 UTC daily (R2 upload, no LLM)
            "options": {"queue": "bulk"},
        },
        "swarm-training": {
            "task": "src.workers.tasks.train_swarm_batch",
            "schedule": crontab(hour=5, minute=0),  # 05:00 UTC daily
            "options": {"queue": "bulk"},
        },
        "billing-renewals": {
            "task": "src.workers.tasks.process_billing_renewals",
            "schedule": crontab(hour=6, minute=30),  # 06:30 UTC daily
            "options": {"queue": "critical"},
        },
        "daily-burn-rate": {
            "task": "src.workers.tasks.send_daily_burn_rate",
            "schedule": crontab(hour=8, minute=0),  # 08:00 UTC daily
            "options": {"queue": "default"},
        },
        # Periodic LLM/embedding tasks — fixed crontabs, offset from each other
        "vector-ingestion": {
            "task": "src.workers.tasks.ingest_scraped_data",
            "schedule": crontab(minute=15, hour="0,6,12,18"),  # every 6h at :15
            "options": {"queue": "bulk"},
        },
        "context-rebuild": {
            "task": "src.workers.tasks.rebuild_all_context",
            "schedule": crontab(minute=45, hour="3,9,15,21"),  # every 6h at :45, offset 3h
            "options": {"queue": "bulk"},
        },
        "session-compression": {
            "task": "src.workers.tasks.compress_sessions",
            "schedule": crontab(minute=30, hour="11,23"),  # every 12h, off-cluster
            "options": {"queue": "bulk"},
        },
        # P3: POS pipeline periodic tasks.
        "pos-incremental-sync": {
            # Every 15 min on the 7s — offset from the :00/:15/:30/:45
            # crons that align at boot, to avoid herding when the
            # entire beat schedule fires together.
            "task": "src.workers.tasks.incremental_sync_all",
            "schedule": crontab(minute="7,22,37,52"),
            "options": {"queue": "default"},
        },
        "pos-token-refresh": {
            # Daily 04:45 UTC — offset from cold-storage (03:30) and
            # billing-renewals (06:30) so token refresh doesn't
            # collide with either. 7-day lookahead window means we
            # have ~6 days of slack before any Square token actually
            # expires.
            "task": "src.workers.tasks.refresh_pos_tokens",
            "schedule": crontab(hour=4, minute=45),
            "options": {"queue": "default"},
        },
    },
)
