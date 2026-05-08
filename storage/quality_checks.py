"""
Data quality validation — gates before every archive and publish.

Uses pandas-native checks (Great Expectations requires heavy setup).
All checks return (passed: bool, errors: list[str]).
"""
import logging

import pandas as pd

logger = logging.getLogger("meridian.storage.quality")

VALID_BUSINESS_TYPES = [
    "restaurant", "fast_food", "coffee_shop", "auto_shop", "smoke_shop",
    "retail", "bar", "bakery", "salon", "other",
]

VALID_POS_SYSTEMS = ["square", "toast", "clover", "lightspeed", "manual"]


def validate_transactions(df: pd.DataFrame) -> tuple[bool, list[str]]:
    errors = []

    for col in ("merchant_id", "transaction_id", "timestamp", "total_cents"):
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    if errors:
        return False, errors

    nulls = df["merchant_id"].isna().sum()
    if nulls > 0:
        errors.append(f"merchant_id has {nulls} null values")

    if "total_cents" in df.columns:
        bad = ((df["total_cents"] < 0) | (df["total_cents"] > 10_000_000)).sum()
        if bad > 0:
            errors.append(f"{bad} transactions with total_cents outside [0, 10M]")

    dupes = df["transaction_id"].duplicated().sum()
    if dupes > 0:
        errors.append(f"{dupes} duplicate transaction_ids")

    passed = len(errors) == 0
    if not passed:
        logger.warning("Transaction validation failed: %s", errors)
    return passed, errors


def validate_heatmaps(df: pd.DataFrame) -> tuple[bool, list[str]]:
    errors = []

    for col in ("merchant_id", "x_coord", "y_coord", "intensity"):
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    if errors:
        return False, errors

    bad_intensity = ((df["intensity"] < 0) | (df["intensity"] > 1.0)).sum()
    if bad_intensity > 0:
        errors.append(f"{bad_intensity} intensity values outside [0, 1]")

    passed = len(errors) == 0
    if not passed:
        logger.warning("Heatmap validation failed: %s", errors)
    return passed, errors


def validate_benchmarks(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    CRITICAL: catch any data that could identify a specific merchant.
    """
    errors = []

    if "merchant_count" in df.columns:
        below_k = (df["merchant_count"] < 5).sum()
        if below_k > 0:
            errors.append(f"PRIVACY VIOLATION: {below_k} rows with merchant_count < 5")

    forbidden_cols = {"merchant_name", "address", "phone", "email", "contact_email", "owner_name"}
    present = forbidden_cols & set(df.columns)
    if present:
        errors.append(f"PRIVACY VIOLATION: PII columns present: {present}")

    if "avg_transaction" in df.columns:
        bad = ((df["avg_transaction"] < 0) | (df["avg_transaction"] > 10_000)).sum()
        if bad > 0:
            errors.append(f"{bad} avg_transaction values outside [0, 10K]")

    passed = len(errors) == 0
    if not passed:
        logger.error("Benchmark validation FAILED: %s", errors)
    return passed, errors
