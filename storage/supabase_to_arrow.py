"""
Supabase → Parquet exporter using Apache Arrow.

Exports merchant data from Supabase into Hive-partitioned Parquet files
for archival on B2 and analytics via DuckDB/Iceberg.

Partition layout:
  data/parquet/transactions/merchant={id}/date={YYYY-MM-DD}/data.parquet
  data/parquet/heatmaps/merchant={id}/date={YYYY-MM-DD}/data.parquet
  data/parquet/insights/date={YYYY-MM-DD}/data.parquet
  data/parquet/foot_traffic/business_type={type}/date={YYYY-MM-DD}/data.parquet
"""
import os
import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger("meridian.storage.export")

DATA_DIR = Path(os.getenv("MERIDIAN_PARQUET_DIR", "./data/parquet"))


def _get_supabase():
    from supabase import create_client
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def _safe_array(rows, key, pa_type=None):
    vals = [r.get(key) for r in rows]
    if pa_type:
        return pa.array(vals, type=pa_type)
    return pa.array(vals)


def export_transactions_to_parquet(merchant_id: str, date: str) -> str | None:
    sb = _get_supabase()
    rows = (
        sb.table("transactions")
        .select("*")
        .eq("org_id", merchant_id)
        .gte("transaction_at", f"{date}T00:00:00Z")
        .lte("transaction_at", f"{date}T23:59:59Z")
        .execute()
        .data
    )
    if not rows:
        return None

    table = pa.table({
        "merchant_id":    _safe_array(rows, "org_id"),
        "transaction_id": _safe_array(rows, "external_id"),
        "timestamp":      _safe_array(rows, "transaction_at"),
        "total_cents":    _safe_array(rows, "total_cents", pa.int64()),
        "subtotal_cents": _safe_array(rows, "subtotal_cents", pa.int64()),
        "tax_cents":      _safe_array(rows, "tax_cents", pa.int64()),
        "tip_cents":      _safe_array(rows, "tip_cents", pa.int64()),
        "discount_cents": _safe_array(rows, "discount_cents", pa.int64()),
        "payment_method": _safe_array(rows, "payment_method"),
        "employee_name":  _safe_array(rows, "employee_name"),
        "type":           _safe_array(rows, "type"),
    })

    out = DATA_DIR / f"transactions/merchant={merchant_id}/date={date}/data.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(out), compression="snappy")
    logger.info("Exported %d transactions → %s", len(rows), out)
    return str(out)


def export_transaction_items_to_parquet(merchant_id: str, date: str) -> str | None:
    sb = _get_supabase()
    rows = (
        sb.table("transaction_items")
        .select("*")
        .eq("org_id", merchant_id)
        .gte("transaction_at", f"{date}T00:00:00Z")
        .lte("transaction_at", f"{date}T23:59:59Z")
        .execute()
        .data
    )
    if not rows:
        return None

    table = pa.table({
        "merchant_id":    _safe_array(rows, "org_id"),
        "transaction_id": _safe_array(rows, "transaction_id"),
        "product_name":   _safe_array(rows, "product_name"),
        "quantity":       _safe_array(rows, "quantity", pa.int32()),
        "unit_price_cents": _safe_array(rows, "unit_price_cents", pa.int64()),
        "total_cents":    _safe_array(rows, "total_cents", pa.int64()),
        "discount_cents": _safe_array(rows, "discount_cents", pa.int64()),
    })

    out = DATA_DIR / f"items/merchant={merchant_id}/date={date}/data.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(out), compression="snappy")
    logger.info("Exported %d items → %s", len(rows), out)
    return str(out)


def export_heatmaps_to_parquet(merchant_id: str, date: str) -> str | None:
    sb = _get_supabase()
    rows = (
        sb.table("heatmap_cells")
        .select("*")
        .eq("merchant_id", merchant_id)
        .gte("recorded_at", f"{date}T00:00:00Z")
        .lte("recorded_at", f"{date}T23:59:59Z")
        .execute()
        .data
    )
    if not rows:
        return None

    table = pa.table({
        "merchant_id":  _safe_array(rows, "merchant_id"),
        "x_coord":      _safe_array(rows, "x", pa.float32()),
        "y_coord":      _safe_array(rows, "y", pa.float32()),
        "intensity":    _safe_array(rows, "intensity", pa.float32()),
        "zone_id":      _safe_array(rows, "zone_id"),
        "recorded_at":  _safe_array(rows, "recorded_at"),
        "time_slot":    _safe_array(rows, "time_slot", pa.int32()),
    })

    out = DATA_DIR / f"heatmaps/merchant={merchant_id}/date={date}/data.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(out), compression="snappy")
    logger.info("Exported %d heatmap cells → %s", len(rows), out)
    return str(out)


def export_insights_to_parquet(date: str) -> str | None:
    sb = _get_supabase()
    rows = (
        sb.table("merchant_insights")
        .select("*")
        .gte("generated_at", f"{date}T00:00:00Z")
        .lte("generated_at", f"{date}T23:59:59Z")
        .execute()
        .data
    )
    if not rows:
        return None

    table = pa.table({
        "insight_id":     _safe_array(rows, "id"),
        "merchant_id":    _safe_array(rows, "merchant_id"),
        "insight_type":   _safe_array(rows, "insight_type"),
        "agent_name":     _safe_array(rows, "agent_name"),
        "revenue_impact": _safe_array(rows, "revenue_impact", pa.float64()),
        "confidence":     _safe_array(rows, "confidence", pa.float32()),
        "acted_on":       _safe_array(rows, "acted_on", pa.bool_()),
        "generated_at":   _safe_array(rows, "generated_at"),
    })

    out = DATA_DIR / f"insights/date={date}/data.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(out), compression="snappy")
    logger.info("Exported %d insights → %s", len(rows), out)
    return str(out)


def export_inventory_to_parquet(merchant_id: str, date: str) -> str | None:
    sb = _get_supabase()
    rows = (
        sb.table("inventory_snapshots")
        .select("*")
        .eq("org_id", merchant_id)
        .gte("snapshot_at", f"{date}T00:00:00Z")
        .lte("snapshot_at", f"{date}T23:59:59Z")
        .execute()
        .data
    )
    if not rows:
        return None

    table = pa.table({
        "merchant_id":       _safe_array(rows, "org_id"),
        "product_id":        _safe_array(rows, "product_id"),
        "location_id":       _safe_array(rows, "location_id"),
        "quantity_on_hand":  _safe_array(rows, "quantity_on_hand", pa.int32()),
        "quantity_sold":     _safe_array(rows, "quantity_sold", pa.int32()),
        "quantity_received": _safe_array(rows, "quantity_received", pa.int32()),
        "quantity_wasted":   _safe_array(rows, "quantity_wasted", pa.int32()),
        "snapshot_at":       _safe_array(rows, "snapshot_at"),
    })

    out = DATA_DIR / f"inventory/merchant={merchant_id}/date={date}/data.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(out), compression="snappy")
    logger.info("Exported %d inventory rows → %s", len(rows), out)
    return str(out)
