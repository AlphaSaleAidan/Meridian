"""
Celery Application — Async task queue for Meridian.

Broker: Redis (configurable via REDIS_URL env var)
Backend: Redis (for result storage)

Tasks are defined in src/workers/tasks.py.
"""
import os

from celery import Celery

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
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "sync": {"exchange": "sync", "routing_key": "sync"},
        "analysis": {"exchange": "analysis", "routing_key": "analysis"},
        "reports": {"exchange": "reports", "routing_key": "reports"},
    },
    task_routes={
        "src.workers.tasks.sync_pos_data": {"queue": "sync"},
        "src.workers.tasks.run_analysis": {"queue": "analysis"},
        "src.workers.tasks.generate_report": {"queue": "reports"},
        "src.workers.tasks.train_swarm": {"queue": "analysis"},
        "src.workers.tasks.train_swarm_batch": {"queue": "analysis"},
    },
    beat_schedule={
        "nightly-analysis": {
            "task": "src.workers.tasks.run_nightly_analysis",
            "schedule": 86400.0,  # 24 hours
            "options": {"queue": "analysis"},
        },
        "weekly-reports": {
            "task": "src.workers.tasks.generate_weekly_reports",
            "schedule": 604800.0,  # 7 days
            "options": {"queue": "reports"},
        },
        "swarm-training": {
            "task": "src.workers.tasks.train_swarm_batch",
            "schedule": 21600.0,  # 6 hours
            "options": {"queue": "analysis"},
        },
        "billing-renewals": {
            "task": "src.workers.tasks.process_billing_renewals",
            "schedule": 86400.0,  # 24 hours
            "options": {"queue": "default"},
        },
    },
)
