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
        "src.workers.tasks.sync_all_pos_incremental": {"queue": "default"},
        "src.workers.tasks.sync_pos_data": {"queue": "default"},
        "src.workers.tasks.run_analysis": {"queue": "default"},
        "src.workers.tasks.process_billing_renewals": {"queue": "critical"},
        # Routed to `default` (a queue the worker actually consumes) — Square
        # OAuth tokens expire in 30 days and this refresh was stranded on the
        # unconsumed `critical` queue, so connections silently died after a
        # month. Safe + idempotent (only refreshes tokens expiring within 7d).
        "src.workers.tasks.refresh_square_tokens": {"queue": "default"},
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
    },
    result_expires=3600,
    worker_max_tasks_per_child=200,
    beat_schedule={
        "pos-incremental-sync": {
            "task": "src.workers.tasks.sync_all_pos_incremental",
            "schedule": 900.0,  # every 15 min — ongoing POS propagation (audit #5)
            "options": {"queue": "default"},
        },
        "nightly-analysis": {
            "task": "src.workers.tasks.run_nightly_analysis",
            "schedule": crontab(hour=2, minute=0),  # 2 AM UTC daily
            "options": {"queue": "bulk"},
        },
        "weekly-reports": {
            "task": "src.workers.tasks.generate_weekly_reports",
            "schedule": crontab(hour=3, minute=0, day_of_week=1),  # Monday 3 AM UTC
            "options": {"queue": "bulk"},
        },
        "swarm-training": {
            "task": "src.workers.tasks.train_swarm_batch",
            "schedule": crontab(hour=5, minute=0),  # 5 AM UTC daily
            "options": {"queue": "bulk"},
        },
        # billing-renewals REMOVED 2026-08-19: it created SQUARE renewal invoices
        # for every subscription past its period. Billing is Stripe-only now, and
        # Stripe subscriptions auto-renew natively (Stripe bills the card on file
        # each period and fires invoice.paid) — there is nothing for a renewal
        # cron to do. process_renewals() is also guarded to a no-op so a manual
        # trigger can't mint Square invoices either.
        "square-token-refresh": {
            "task": "src.workers.tasks.refresh_square_tokens",
            "schedule": crontab(hour=7, minute=0),  # 7 AM UTC daily
            "options": {"queue": "default"},  # default IS consumed (was stranded on critical)
        },
        "daily-burn-rate": {
            "task": "src.workers.tasks.send_daily_burn_rate",
            "schedule": crontab(hour=8, minute=0),  # 8 AM UTC daily
            "options": {"queue": "default"},
        },
        "waitlist-offer-expiry": {
            "task": "src.workers.tasks.expire_waitlist_offers",
            "schedule": 120.0,  # every 2 min — must be well under the offer window
            "options": {"queue": "default"},
        },
        "booking-calendar-sync": {
            "task": "src.workers.tasks.sync_booking_calendars",
            "schedule": 1200.0,  # every 20 min — see the task docstring
            "options": {"queue": "default"},
        },
        "booking-reminders": {
            "task": "src.workers.tasks.send_booking_reminders",
            "schedule": 900.0,  # every 15 min — see the task docstring
            "options": {"queue": "default"},
        },
        "phone-vocab-mining": {
            "task": "src.workers.tasks.mine_phone_vocab",
            "schedule": crontab(hour=9, minute=30),  # 9:30 AM UTC daily
            "options": {"queue": "bulk"},
        },
        "careers-reconcile": {
            "task": "src.workers.tasks.reconcile_careers_applicants",
            "schedule": crontab(hour=15, minute=0),  # 3 PM UTC daily (morning PT) — applicant visibility invariant
            "options": {"queue": "default"},
        },
        "vector-ingestion": {
            "task": "src.workers.tasks.ingest_scraped_data",
            "schedule": 21600.0,  # 6 hours — after each scraper cycle
            "options": {"queue": "bulk"},
        },
        "context-rebuild": {
            "task": "src.workers.tasks.rebuild_all_context",
            "schedule": 21600.0,  # 6 hours — full token-saving pipeline
            "options": {"queue": "bulk"},
        },
        "session-compression": {
            "task": "src.workers.tasks.compress_sessions",
            "schedule": 43200.0,  # 12 hours — compress completed Claude sessions
            "options": {"queue": "bulk"},
        },
        "cold-storage-archive": {
            "task": "src.workers.tasks.run_cold_storage_archive",
            "schedule": crontab(hour=4, minute=0),  # 4 AM UTC daily
            "options": {"queue": "bulk"},
        },
    },
)
