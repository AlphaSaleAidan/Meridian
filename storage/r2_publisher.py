"""
Cloudflare R2 publisher — buyer-facing delivery tier ($0.015/GB, $0 egress).

Publishes anonymized datasets and generates presigned download URLs
for paying customers.

Bucket structure:
  meridian-marketplace/
    datasets/meridian_benchmarks_{YYYY-MM}.parquet
    datasets/meridian_foot_traffic_{business_type}_{YYYY-MM}.parquet
    datasets/meridian_foot_traffic_all_{YYYY-MM}.parquet
    samples/meridian_sample_100rows.parquet
"""
import os
import logging

import boto3

logger = logging.getLogger("meridian.storage.r2")


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['CF_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY"],
        aws_secret_access_key=os.environ["R2_SECRET_KEY"],
        region_name="auto",
    )


def publish_benchmark_dataset(month: str):
    s3 = get_r2_client()
    local_path = f"./data/parquet/benchmarks/month={month}/benchmarks.parquet"
    remote_key = f"datasets/meridian_benchmarks_{month}.parquet"
    s3.upload_file(local_path, os.environ["R2_BUCKET"], remote_key)
    logger.info("Published benchmarks to R2: %s", remote_key)


def publish_foot_traffic_dataset(month: str, business_type: str | None = None):
    s3 = get_r2_client()
    if business_type:
        local_path = f"./data/parquet/foot_traffic/business_type={business_type}/month={month}/data.parquet"
        remote_key = f"datasets/meridian_foot_traffic_{business_type}_{month}.parquet"
    else:
        local_path = f"./data/parquet/foot_traffic/month={month}/data.parquet"
        remote_key = f"datasets/meridian_foot_traffic_all_{month}.parquet"
    s3.upload_file(local_path, os.environ["R2_BUCKET"], remote_key)
    logger.info("Published foot traffic to R2: %s", remote_key)


def generate_buyer_download_url(
    remote_key: str,
    expiry_hours: int = 24,
) -> str:
    """
    Generate a time-limited presigned URL for a data buyer.
    Called after Stripe payment confirmation.
    Zero egress cost on R2 regardless of download size.
    """
    s3 = get_r2_client()
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": os.environ["R2_BUCKET"], "Key": remote_key},
        ExpiresIn=expiry_hours * 3600,
    )
    logger.info("Generated buyer URL for %s (expires %dh)", remote_key, expiry_hours)
    return url


def list_available_datasets() -> list[dict]:
    s3 = get_r2_client()
    resp = s3.list_objects_v2(
        Bucket=os.environ["R2_BUCKET"],
        Prefix="datasets/",
    )
    return [
        {"key": obj["Key"], "size_mb": round(obj["Size"] / 1_048_576, 2), "modified": obj["LastModified"].isoformat()}
        for obj in resp.get("Contents", [])
    ]
