"""
Anonymization layer for Meridian data.

NON-NEGOTIABLE RULES:
  - merchant_id → one-way SHA-256 hash (same merchant = same anon ID)
  - No merchant name, address, or contact info in any external dataset
  - k-anonymity: no cell with fewer than MIN_MERCHANTS merchants
  - PIPEDA (Canada) + US de-identification best practices
"""
import hashlib
import logging

import pandas as pd

logger = logging.getLogger("meridian.storage.anonymizer")

MIN_MERCHANTS = 5


def anonymize_merchant_id(merchant_id: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{merchant_id}".encode()).hexdigest()[:16]


def create_benchmark_dataset(
    transactions_df: pd.DataFrame,
    salt: str,
    min_merchants: int = MIN_MERCHANTS,
) -> pd.DataFrame:
    """
    Aggregate transaction data into anonymized industry benchmarks.
    Groups by business_type, region, and month.
    """
    if transactions_df.empty:
        return pd.DataFrame()

    df = transactions_df.copy()
    df["month"] = pd.to_datetime(df["timestamp"]).dt.to_period("M").astype(str)
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date.astype(str)
    df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
    df["amount"] = df["total_cents"] / 100.0

    if "region" not in df.columns:
        df["region"] = "unknown"
    if "business_type" not in df.columns:
        df["business_type"] = "other"

    grouped = df.groupby(["business_type", "region", "month"])

    benchmarks = []
    for (btype, region, month), group in grouped:
        merchant_count = group["merchant_id"].nunique()
        if merchant_count < min_merchants:
            continue

        daily_revenue = group.groupby("date")["amount"].sum()
        benchmarks.append({
            "month": month,
            "business_type": btype,
            "region": region,
            "avg_transaction": round(group["amount"].mean(), 2),
            "median_transaction": round(group["amount"].median(), 2),
            "avg_daily_revenue": round(daily_revenue.mean(), 2),
            "p25_daily_revenue": round(daily_revenue.quantile(0.25), 2),
            "p75_daily_revenue": round(daily_revenue.quantile(0.75), 2),
            "peak_hour": int(group.groupby("hour")["amount"].sum().idxmax()),
            "avg_items_per_transaction": round(
                group["item_count"].mean(), 1
            ) if "item_count" in group.columns else None,
            "merchant_count": merchant_count,
            "transaction_count": len(group),
            "currency": "USD",
        })

    result = pd.DataFrame(benchmarks)
    logger.info(
        "Generated %d benchmark rows (dropped %d groups below k=%d)",
        len(result),
        len(grouped) - len(result),
        min_merchants,
    )
    return result


def create_foot_traffic_dataset(
    heatmap_df: pd.DataFrame,
    min_merchants: int = MIN_MERCHANTS,
) -> pd.DataFrame:
    """
    Aggregate camera heatmap data into anonymized foot traffic intelligence.
    """
    if heatmap_df.empty:
        return pd.DataFrame()

    df = heatmap_df.copy()
    if "region" not in df.columns:
        df["region"] = "unknown"
    if "business_type" not in df.columns:
        df["business_type"] = "other"

    grouped = df.groupby(["business_type", "region", "date", "time_slot"])

    records = []
    for (btype, region, date, hour), group in grouped:
        merchant_count = group["merchant_id"].nunique()
        if merchant_count < min_merchants:
            continue

        records.append({
            "date": str(date),
            "business_type": btype,
            "region": region,
            "hour_slot": int(hour),
            "avg_intensity": round(group["intensity"].mean(), 4),
            "max_intensity": round(group["intensity"].max(), 4),
            "zone_count": group["zone_id"].nunique(),
            "merchant_count": merchant_count,
        })

    result = pd.DataFrame(records)
    logger.info("Generated %d foot traffic rows", len(result))
    return result
