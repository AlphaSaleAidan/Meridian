"""
Backblaze B2 uploader — primary archive tier ($0.006/GB).

Uploads Parquet files to B2 maintaining the same Hive partition layout.

Bucket structure:
  meridian-data-raw/
    transactions/merchant={id}/date={YYYY-MM-DD}/data.parquet
    items/merchant={id}/date={YYYY-MM-DD}/data.parquet
    heatmaps/merchant={id}/date={YYYY-MM-DD}/data.parquet
    insights/date={YYYY-MM-DD}/data.parquet
    inventory/merchant={id}/date={YYYY-MM-DD}/data.parquet
    benchmarks/month={YYYY-MM}/benchmarks.parquet
    spaces/merchant={id}/space={id}/pointcloud.ply
"""
import os
import logging

from b2sdk.v2 import InMemoryAccountInfo, B2Api

logger = logging.getLogger("meridian.storage.b2")


def get_b2_api() -> B2Api:
    info = InMemoryAccountInfo()
    api = B2Api(info)
    api.authorize_account(
        "production",
        os.environ["B2_KEY_ID"],
        os.environ["B2_APP_KEY"],
    )
    return api


def upload_to_b2(local_path: str, remote_key: str) -> str:
    api = get_b2_api()
    bucket = api.get_bucket_by_name(os.environ["B2_BUCKET_RAW"])
    file_version = bucket.upload_local_file(
        local_file=local_path,
        file_name=remote_key,
    )
    logger.info("B2 upload: %s → %s", local_path, remote_key)
    return file_version.id_


def upload_merchant_daily(merchant_id: str, date: str):
    """Upload all daily Parquet files for one merchant."""
    from pathlib import Path
    base = Path(os.getenv("MERIDIAN_PARQUET_DIR", "./data/parquet"))

    for dataset in ("transactions", "items", "heatmaps", "inventory"):
        local = base / f"{dataset}/merchant={merchant_id}/date={date}/data.parquet"
        if local.exists():
            upload_to_b2(
                str(local),
                f"{dataset}/merchant={merchant_id}/date={date}/data.parquet",
            )


def upload_insights(date: str):
    from pathlib import Path
    local = Path(os.getenv("MERIDIAN_PARQUET_DIR", "./data/parquet")) / f"insights/date={date}/data.parquet"
    if local.exists():
        upload_to_b2(str(local), f"insights/date={date}/data.parquet")


def upload_3d_space(merchant_id: str, space_id: str, ply_path: str):
    upload_to_b2(
        ply_path,
        f"spaces/merchant={merchant_id}/space={space_id}/pointcloud.ply",
    )


def upload_benchmarks(month: str):
    from pathlib import Path
    local = Path(os.getenv("MERIDIAN_PARQUET_DIR", "./data/parquet")) / f"benchmarks/month={month}/benchmarks.parquet"
    if local.exists():
        upload_to_b2(str(local), f"benchmarks/month={month}/benchmarks.parquet")
