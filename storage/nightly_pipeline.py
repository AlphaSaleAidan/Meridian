"""
Nightly storage pipeline — Supabase → Parquet → validate → B2 archive → R2 publish.

Schedule: 1:30 AM daily (before Ruflo's 3 AM agent run)

Monthly (1st of month): generate anonymized benchmarks and publish to R2 marketplace.
"""
import os
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from .supabase_to_arrow import (
    export_transactions_to_parquet,
    export_transaction_items_to_parquet,
    export_heatmaps_to_parquet,
    export_insights_to_parquet,
    export_inventory_to_parquet,
)
from .quality_checks import validate_transactions, validate_benchmarks
from .anonymizer import create_benchmark_dataset

logger = logging.getLogger("meridian.storage.pipeline")

PARQUET_DIR = Path(os.getenv("MERIDIAN_PARQUET_DIR", "./data/parquet"))
ANON_SALT = os.getenv("ANONYMIZATION_SALT", "meridian-default-salt-change-me")


def _get_active_merchants() -> list[dict]:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    result = sb.table("organizations").select("id, name, business_type, state").eq("status", "active").execute()
    return result.data or []


def run_daily_export(target_date: str | None = None):
    """Export all merchant data for one day to Parquet."""
    today = target_date or (date.today() - timedelta(days=1)).isoformat()
    merchants = _get_active_merchants()
    logger.info("Starting daily export for %s (%d merchants)", today, len(merchants))

    exported = 0
    failed = 0

    for merchant in merchants:
        mid = merchant["id"]
        try:
            tx_path = export_transactions_to_parquet(mid, today)
            export_transaction_items_to_parquet(mid, today)
            export_heatmaps_to_parquet(mid, today)
            export_inventory_to_parquet(mid, today)

            if tx_path:
                df = pd.read_parquet(tx_path)
                passed, errors = validate_transactions(df)
                if not passed:
                    logger.warning("Quality check failed for %s: %s", mid, errors)
                    failed += 1
                    continue

            exported += 1
        except Exception as e:
            logger.error("Export failed for merchant %s: %s", mid, e)
            failed += 1

    export_insights_to_parquet(today)

    logger.info("Daily export complete: %d exported, %d failed", exported, failed)
    return {"date": today, "exported": exported, "failed": failed}


def run_b2_upload(target_date: str | None = None):
    """Upload today's Parquet files to B2 archive."""
    if not os.environ.get("B2_KEY_ID"):
        logger.info("B2 not configured — skipping upload")
        return

    from .b2_uploader import upload_merchant_daily, upload_insights

    today = target_date or (date.today() - timedelta(days=1)).isoformat()
    merchants = _get_active_merchants()

    for merchant in merchants:
        try:
            upload_merchant_daily(merchant["id"], today)
        except Exception as e:
            logger.error("B2 upload failed for %s: %s", merchant["id"], e)

    try:
        upload_insights(today)
    except Exception as e:
        logger.error("B2 insights upload failed: %s", e)

    logger.info("B2 upload complete for %s", today)


def run_monthly_benchmarks():
    """Generate and publish anonymized benchmarks (run on 1st of month)."""
    last_month_end = date.today().replace(day=1) - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    month_str = last_month_start.strftime("%Y-%m")

    logger.info("Generating benchmarks for %s", month_str)

    all_files = list(PARQUET_DIR.glob(f"transactions/merchant=*/date={last_month_start.isoformat()}*/data.parquet"))
    for d in range((last_month_end - last_month_start).days + 1):
        day = (last_month_start + timedelta(days=d)).isoformat()
        all_files.extend(PARQUET_DIR.glob(f"transactions/merchant=*/date={day}/data.parquet"))

    if not all_files:
        logger.warning("No transaction files found for %s", month_str)
        return

    dfs = [pd.read_parquet(f) for f in all_files]
    combined = pd.concat(dfs, ignore_index=True)

    benchmarks = create_benchmark_dataset(combined, salt=ANON_SALT)

    passed, errors = validate_benchmarks(benchmarks)
    if not passed:
        logger.error("Benchmark validation FAILED — aborting publish: %s", errors)
        return

    out_dir = PARQUET_DIR / f"benchmarks/month={month_str}"
    out_dir.mkdir(parents=True, exist_ok=True)
    benchmarks.to_parquet(out_dir / "benchmarks.parquet", compression="snappy", index=False)
    logger.info("Benchmarks saved: %d rows for %s", len(benchmarks), month_str)

    if os.environ.get("B2_KEY_ID"):
        from .b2_uploader import upload_benchmarks
        upload_benchmarks(month_str)

    if os.environ.get("R2_ACCESS_KEY"):
        from .r2_publisher import publish_benchmark_dataset
        publish_benchmark_dataset(month_str)

    logger.info("Monthly benchmarks published for %s", month_str)


def run_full_pipeline(target_date: str | None = None):
    """Run the complete nightly pipeline."""
    result = run_daily_export(target_date)
    run_b2_upload(target_date)

    if date.today().day == 1:
        run_monthly_benchmarks()

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_full_pipeline()
