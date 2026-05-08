"""
Apache Iceberg catalog — versioned, queryable table format.

Wraps Parquet files in metadata so the full dataset is queryable
from DuckDB, Spark, Trino, Snowflake, or Athena with time travel.
"""
import os
import logging

from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField, StringType, LongType, DoubleType,
    BooleanType, TimestampType, FloatType, IntegerType,
)

logger = logging.getLogger("meridian.storage.iceberg")


def get_catalog():
    return load_catalog("meridian", **{
        "type": "rest",
        "uri": os.getenv("ICEBERG_REST_URI", "http://localhost:8181"),
        "s3.endpoint": os.environ.get("B2_ENDPOINT", ""),
        "s3.access-key-id": os.environ.get("B2_KEY_ID", ""),
        "s3.secret-access-key": os.environ.get("B2_APP_KEY", ""),
    })


TRANSACTION_SCHEMA = Schema(
    NestedField(1,  "transaction_id",  StringType(),    required=True),
    NestedField(2,  "merchant_id",     StringType(),    required=True),
    NestedField(3,  "timestamp",       TimestampType(), required=True),
    NestedField(4,  "total_cents",     LongType()),
    NestedField(5,  "subtotal_cents",  LongType()),
    NestedField(6,  "tax_cents",       LongType()),
    NestedField(7,  "tip_cents",       LongType()),
    NestedField(8,  "discount_cents",  LongType()),
    NestedField(9,  "payment_method",  StringType()),
    NestedField(10, "employee_name",   StringType()),
    NestedField(11, "type",            StringType()),
)

BENCHMARK_SCHEMA = Schema(
    NestedField(1,  "month",               StringType(),  required=True),
    NestedField(2,  "business_type",       StringType(),  required=True),
    NestedField(3,  "region",              StringType()),
    NestedField(4,  "avg_transaction",     DoubleType()),
    NestedField(5,  "median_transaction",  DoubleType()),
    NestedField(6,  "avg_daily_revenue",   DoubleType()),
    NestedField(7,  "p25_daily_revenue",   DoubleType()),
    NestedField(8,  "p75_daily_revenue",   DoubleType()),
    NestedField(9,  "peak_hour",           IntegerType()),
    NestedField(10, "merchant_count",      IntegerType()),
    NestedField(11, "transaction_count",   IntegerType()),
    NestedField(12, "currency",            StringType()),
)

FOOT_TRAFFIC_SCHEMA = Schema(
    NestedField(1,  "date",              StringType(),  required=True),
    NestedField(2,  "business_type",     StringType(),  required=True),
    NestedField(3,  "hour_slot",         IntegerType()),
    NestedField(4,  "avg_intensity",     FloatType()),
    NestedField(5,  "max_intensity",     FloatType()),
    NestedField(6,  "zone_count",        IntegerType()),
    NestedField(7,  "region",            StringType()),
    NestedField(8,  "merchant_count",    IntegerType()),
)


def create_tables():
    catalog = get_catalog()
    catalog.create_namespace_if_not_exists("meridian")

    for name, schema in [
        ("meridian.transactions", TRANSACTION_SCHEMA),
        ("meridian.benchmarks", BENCHMARK_SCHEMA),
        ("meridian.foot_traffic", FOOT_TRAFFIC_SCHEMA),
    ]:
        try:
            catalog.create_table(name, schema)
            logger.info("Created Iceberg table: %s", name)
        except Exception:
            logger.debug("Table %s already exists", name)
