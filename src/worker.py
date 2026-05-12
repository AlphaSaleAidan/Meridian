"""
Worker entrypoint — starts the Celery worker with beat scheduler.

Usage: python3 -m src.worker
"""
import sys
import os

from src.workers.celery_app import celery_app


def main():
    loglevel = os.environ.get("CELERY_LOG_LEVEL", "info")
    queues = os.environ.get("CELERY_QUEUES", "default,sync,analysis,reports")
    concurrency = os.environ.get("CELERY_CONCURRENCY", "4")

    argv = [
        "worker",
        f"--loglevel={loglevel}",
        f"--concurrency={concurrency}",
        f"--queues={queues}",
        "--beat",
        "--without-gossip",
        "--without-mingle",
    ]

    celery_app.worker_main(argv)


if __name__ == "__main__":
    main()
