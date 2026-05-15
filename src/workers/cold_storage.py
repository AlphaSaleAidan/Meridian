"""
Cold Storage Pipeline — Compress and archive historical data for long-term storage,
resale packaging, and swarm training.

Three-tier storage:
  HOT   — Supabase/PostgreSQL (last 90 days, live queries)
  WARM  — Local compressed archives (last 12 months, fast retrieval)
  COLD  — Object storage R2/S3 (all history, resale-ready)

Six data tiers (by category):
  A. POS & Revenue       — transactions, daily/hourly revenue, products, categories
  B. Vision & Foot Traffic — traffic buckets, visits, visitors, cameras, customer profiles
  C. Cross-Reference     — customer journeys, zone correlations, cross-ref insights
  D. AI & Reasoning      — insights, reasoning chains, cline conversations/messages,
                           merchant health, swarm training outputs
  E. Operations          — email logs, phone calls/orders, website analytics/orders,
                           POS connections, commissions, notifications
  F. Spatial & Engagement — 3D spaces, space zones, security events

Archive format:
  data/archives/{org_id}/{year}/{month}/
    ├── tier_a_pos/
    │   ├── transactions.jsonl.zst
    │   ├── products.jsonl.zst
    │   ├── product_categories.jsonl.zst
    │   ├── daily_revenue.jsonl.zst
    │   └── hourly_revenue.jsonl.zst
    ├── tier_b_vision/
    │   ├── vision_traffic.jsonl.zst
    │   ├── vision_visits.jsonl.zst
    │   ├── vision_visitors.jsonl.zst
    │   └── anonymous_customer_profiles.jsonl.zst
    ├── tier_c_crossref/
    │   ├── customer_journeys.jsonl.zst
    │   ├── zone_purchase_correlation.jsonl.zst
    │   └── cross_reference_insights.jsonl.zst
    ├── tier_d_ai/
    │   ├── insights.jsonl.zst
    │   ├── agent_reasoning_chains.jsonl.zst
    │   ├── cline_conversations.jsonl.zst
    │   ├── cline_messages.jsonl.zst
    │   ├── cline_errors.jsonl.zst
    │   └── merchant_health.jsonl.zst
    ├── tier_e_ops/
    │   ├── email_send_log.jsonl.zst
    │   ├── phone_call_logs.jsonl.zst
    │   ├── phone_orders.jsonl.zst
    │   ├── website_analytics.jsonl.zst
    │   ├── website_orders.jsonl.zst
    │   ├── commissions.jsonl.zst
    │   ├── notifications.jsonl.zst
    │   └── checkout_sessions.jsonl.zst
    ├── tier_f_spatial/
    │   ├── spaces.jsonl.zst
    │   ├── space_zones.jsonl.zst
    │   └── security_events.jsonl.zst
    └── manifest.json

Runs nightly via Celery Beat. Configurable retention window.
"""
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("meridian.workers.cold_storage")

ARCHIVE_DIR = Path(os.getenv("MERIDIAN_ARCHIVE_DIR", "/root/Meridian/data/archives"))
HOT_RETENTION_DAYS = int(os.getenv("MERIDIAN_HOT_RETENTION_DAYS", "90"))

ARCHIVE_TIERS = {
    "tier_a_pos": {
        "label": "POS & Revenue",
        "resale_tier": "premium",
        "tables": [
            {"table": "transactions", "time_column": "created_at", "org_column": "org_id"},
            {"table": "products", "time_column": "updated_at", "org_column": "org_id"},
            {"table": "product_categories", "time_column": "created_at", "org_column": "org_id"},
            {"table": "daily_revenue", "time_column": "date", "org_column": "org_id"},
            {"table": "hourly_revenue", "time_column": "date", "org_column": "org_id"},
        ],
    },
    "tier_b_vision": {
        "label": "Vision & Foot Traffic",
        "resale_tier": "premium",
        "tables": [
            {"table": "vision_traffic", "time_column": "bucket", "org_column": "org_id"},
            {"table": "vision_visits", "time_column": "entered_at", "org_column": "org_id"},
            {"table": "vision_visitors", "time_column": "created_at", "org_column": "org_id"},
            {"table": "anonymous_customer_profiles", "time_column": "last_seen", "org_column": "org_id"},
        ],
    },
    "tier_c_crossref": {
        "label": "Cross-Reference & Journeys",
        "resale_tier": "premium",
        "tables": [
            {"table": "customer_journeys", "time_column": "entry_time", "org_column": "org_id"},
            {"table": "zone_purchase_correlation", "time_column": "period_start", "org_column": "org_id"},
            {"table": "cross_reference_insights", "time_column": "created_at", "org_column": "org_id"},
        ],
    },
    "tier_d_ai": {
        "label": "AI & Reasoning",
        "resale_tier": "high",
        "tables": [
            {"table": "insights", "time_column": "created_at", "org_column": "org_id"},
            {"table": "agent_reasoning_chains", "time_column": "created_at", "org_column": "business_id"},
            {"table": "cline_conversations", "time_column": "created_at", "org_column": "business_id"},
            {"table": "cline_messages", "time_column": "created_at", "org_column": None},
            {"table": "cline_errors", "time_column": "created_at", "org_column": "business_id"},
            {"table": "merchant_health", "time_column": "created_at", "org_column": "business_id"},
        ],
    },
    "tier_e_ops": {
        "label": "Operations & Engagement",
        "resale_tier": "aggregated",
        "tables": [
            {"table": "email_send_log", "time_column": "created_at", "org_column": "org_id"},
            {"table": "phone_call_logs", "time_column": "created_at", "org_column": "merchant_id"},
            {"table": "phone_orders", "time_column": "created_at", "org_column": "merchant_id"},
            {"table": "website_analytics", "time_column": "created_at", "org_column": "org_id"},
            {"table": "website_orders", "time_column": "created_at", "org_column": "org_id"},
            {"table": "commissions", "time_column": "created_at", "org_column": "org_id"},
            {"table": "notifications", "time_column": "created_at", "org_column": "org_id"},
            {"table": "checkout_sessions", "time_column": "created_at", "org_column": "org_id"},
        ],
    },
    "tier_f_spatial": {
        "label": "Spatial & Security",
        "resale_tier": "high",
        "tables": [
            {"table": "spaces", "time_column": "created_at", "org_column": "org_id"},
            {"table": "space_zones", "time_column": "created_at", "org_column": None},
            {"table": "security_events", "time_column": "timestamp", "org_column": None},
        ],
    },
}

def _all_archivable_tables() -> list[tuple[str, dict]]:
    """Flatten tiers into (tier_name, table_cfg) pairs."""
    result = []
    for tier_name, tier in ARCHIVE_TIERS.items():
        for tbl in tier["tables"]:
            result.append((tier_name, {**tbl, "columns": "*"}))
    return result


def _compress_zstd(data: bytes) -> bytes:
    try:
        import zstandard as zstd
        cctx = zstd.ZstdCompressor(level=9)
        return cctx.compress(data)
    except ImportError:
        import gzip
        return gzip.compress(data, compresslevel=9)


def _decompress(data: bytes) -> bytes:
    try:
        import zstandard as zstd
        dctx = zstd.ZstdDecompressor()
        return dctx.decompress(data)
    except ImportError:
        import gzip
        return gzip.decompress(data)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _month_range(year: int, month: int) -> tuple[str, str]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start.isoformat(), end.isoformat()


async def _fetch_table_slice(db, table_cfg: dict, org_id: str, start_iso: str, end_iso: str) -> list[dict]:
    table = table_cfg["table"]
    time_col = table_cfg["time_column"]
    org_col = table_cfg["org_column"]

    filters = {time_col: f"gte.{start_iso}"}
    if org_col:
        filters[org_col] = f"eq.{org_id}"

    try:
        rows = await db.select(table, columns=table_cfg["columns"], filters=filters, order=f"{time_col}.asc", limit=50000)
        return [r for r in rows if r.get(time_col, "") < end_iso]
    except Exception as e:
        logger.warning("Failed to fetch %s for %s: %s", table, org_id, e)
        return []


def _write_archive(org_id: str, year: int, month: int, tier_name: str, table_name: str, rows: list[dict]) -> dict:
    tier_dir = ARCHIVE_DIR / org_id / str(year) / f"{month:02d}" / tier_name
    tier_dir.mkdir(parents=True, exist_ok=True)

    jsonl = "\n".join(json.dumps(r, default=str) for r in rows).encode("utf-8")
    compressed = _compress_zstd(jsonl)

    ext = ".jsonl.zst"
    try:
        import zstandard
    except ImportError:
        ext = ".jsonl.gz"

    filepath = tier_dir / f"{table_name}{ext}"
    filepath.write_bytes(compressed)

    return {
        "tier": tier_name,
        "table": table_name,
        "rows": len(rows),
        "raw_bytes": len(jsonl),
        "compressed_bytes": len(compressed),
        "ratio": round(len(jsonl) / max(len(compressed), 1), 1),
        "sha256": _sha256(compressed),
        "file": str(filepath),
    }


def _write_manifest(org_id: str, year: int, month: int, table_stats: list[dict], duration_sec: float):
    org_dir = ARCHIVE_DIR / org_id / str(year) / f"{month:02d}"

    tier_summaries = {}
    for s in table_stats:
        t = s.get("tier", "unknown")
        if t not in tier_summaries:
            tier_summaries[t] = {"label": ARCHIVE_TIERS.get(t, {}).get("label", t),
                                 "resale_tier": ARCHIVE_TIERS.get(t, {}).get("resale_tier", "unknown"),
                                 "tables": 0, "rows": 0, "raw_bytes": 0, "compressed_bytes": 0}
        tier_summaries[t]["tables"] += 1
        tier_summaries[t]["rows"] += s["rows"]
        tier_summaries[t]["raw_bytes"] += s["raw_bytes"]
        tier_summaries[t]["compressed_bytes"] += s["compressed_bytes"]

    manifest = {
        "org_id": org_id,
        "period": f"{year}-{month:02d}",
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(duration_sec, 2),
        "tiers": tier_summaries,
        "tables": table_stats,
        "total_tables": len(table_stats),
        "total_rows": sum(t["rows"] for t in table_stats),
        "total_raw_bytes": sum(t["raw_bytes"] for t in table_stats),
        "total_compressed_bytes": sum(t["compressed_bytes"] for t in table_stats),
        "overall_ratio": round(
            sum(t["raw_bytes"] for t in table_stats) /
            max(sum(t["compressed_bytes"] for t in table_stats), 1),
            1,
        ),
    }
    (org_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


async def archive_org_month(org_id: str, year: int, month: int, db=None, tiers: list[str] | None = None) -> dict:
    if db is None:
        from ..db import _db_instance
        db = _db_instance
    if not db:
        return {"error": "Database not available"}

    start_iso, end_iso = _month_range(year, month)
    t0 = time.monotonic()

    table_stats = []
    for tier_name, cfg in _all_archivable_tables():
        if tiers and tier_name not in tiers:
            continue

        rows = await _fetch_table_slice(db, cfg, org_id, start_iso, end_iso)
        if rows:
            stats = _write_archive(org_id, year, month, tier_name, cfg["table"], rows)
            table_stats.append(stats)
            logger.info(
                "Archived %s/%s/%s %d-%02d: %d rows, %s → %s (%.1fx)",
                org_id[:8], tier_name, cfg["table"], year, month,
                stats["rows"], _fmt_bytes(stats["raw_bytes"]),
                _fmt_bytes(stats["compressed_bytes"]), stats["ratio"],
            )

    duration = time.monotonic() - t0
    if table_stats:
        manifest = _write_manifest(org_id, year, month, table_stats, duration)
        return manifest
    return {"org_id": org_id, "period": f"{year}-{month:02d}", "tiers": {}, "tables": [], "total_rows": 0}


async def run_nightly_archive():
    from ..db import _db_instance as db
    if not db:
        logger.error("Cold storage: database not available")
        return {"error": "Database not available"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=HOT_RETENTION_DAYS)
    target_year = cutoff.year
    target_month = cutoff.month

    try:
        orgs = await db.select("organizations", columns="id", limit=10000)
    except Exception as e:
        logger.error("Failed to list orgs for archival: %s", e)
        return {"error": str(e)}

    results = []
    for org in orgs:
        org_id = org.get("id", "")
        if not org_id:
            continue

        archive_dir = ARCHIVE_DIR / org_id / str(target_year) / f"{target_month:02d}"
        if (archive_dir / "manifest.json").exists():
            continue

        try:
            result = await archive_org_month(org_id, target_year, target_month, db)
            if result.get("total_rows", 0) > 0:
                results.append(result)
                logger.info(
                    "Archived %s for %d-%02d: %d rows, %s compressed",
                    org_id[:8], target_year, target_month,
                    result["total_rows"], _fmt_bytes(result.get("total_compressed_bytes", 0)),
                )
        except Exception as e:
            logger.error("Archive failed for %s: %s", org_id, e)
            results.append({"org_id": org_id, "error": str(e)})

    total_rows = sum(r.get("total_rows", 0) for r in results)
    total_bytes = sum(r.get("total_compressed_bytes", 0) for r in results)
    logger.info(
        "Nightly archive complete: %d orgs, %d total rows, %s compressed",
        len(results), total_rows, _fmt_bytes(total_bytes),
    )
    return {
        "period": f"{target_year}-{target_month:02d}",
        "orgs_archived": len(results),
        "total_rows": total_rows,
        "total_compressed_bytes": total_bytes,
    }


async def upload_to_r2(org_id: str, year: int, month: int) -> dict:
    """Upload local archive to Cloudflare R2 (or S3-compatible) cold storage."""
    r2_endpoint = os.getenv("R2_ENDPOINT", "")
    r2_access_key = os.getenv("R2_ACCESS_KEY_ID", "")
    r2_secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "")
    r2_bucket = os.getenv("R2_BUCKET", "meridian-archives")

    if not r2_endpoint or not r2_access_key:
        return {"status": "skipped", "reason": "R2 not configured"}

    try:
        import boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=r2_access_key,
            aws_secret_access_key=r2_secret_key,
        )
    except ImportError:
        return {"status": "error", "reason": "boto3 not installed"}

    org_dir = ARCHIVE_DIR / org_id / str(year) / f"{month:02d}"
    if not org_dir.exists():
        return {"status": "skipped", "reason": "No local archive"}

    uploaded = []
    for f in org_dir.rglob("*"):
        if f.is_file():
            rel = f.relative_to(ARCHIVE_DIR)
            s3.upload_file(str(f), r2_bucket, str(rel))
            uploaded.append(str(rel))

    logger.info("Uploaded %d files to R2 for %s/%d-%02d", len(uploaded), org_id[:8], year, month)
    return {"status": "uploaded", "files": uploaded, "bucket": r2_bucket}


def read_archive(org_id: str, year: int, month: int, table_name: str) -> list[dict]:
    """Read a compressed archive back into memory. Searches tier subdirs and flat layout."""
    org_dir = ARCHIVE_DIR / org_id / str(year) / f"{month:02d}"

    for ext in [".jsonl.zst", ".jsonl.gz"]:
        filepath = org_dir / f"{table_name}{ext}"
        if filepath.exists():
            raw = _decompress(filepath.read_bytes())
            return [json.loads(line) for line in raw.decode("utf-8").strip().split("\n") if line]

        for tier_dir in org_dir.iterdir():
            if tier_dir.is_dir():
                tier_path = tier_dir / f"{table_name}{ext}"
                if tier_path.exists():
                    raw = _decompress(tier_path.read_bytes())
                    return [json.loads(line) for line in raw.decode("utf-8").strip().split("\n") if line]

    return []


def list_archives(org_id: str | None = None) -> list[dict]:
    """List all available archives, optionally filtered by org."""
    archives = []
    search_dir = ARCHIVE_DIR / org_id if org_id else ARCHIVE_DIR

    if not search_dir.exists():
        return []

    for manifest_path in search_dir.rglob("manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text())
            archives.append(manifest)
        except Exception:
            pass

    return sorted(archives, key=lambda a: a.get("period", ""), reverse=True)


def get_archive_stats() -> dict:
    """Get total archive storage statistics."""
    if not ARCHIVE_DIR.exists():
        return {"total_archives": 0, "total_bytes": 0, "orgs": 0}

    total_bytes = 0
    org_ids = set()
    archive_count = 0

    for manifest_path in ARCHIVE_DIR.rglob("manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text())
            total_bytes += manifest.get("total_compressed_bytes", 0)
            org_ids.add(manifest.get("org_id", ""))
            archive_count += 1
        except Exception:
            pass

    return {
        "total_archives": archive_count,
        "total_compressed_bytes": total_bytes,
        "total_compressed_mb": round(total_bytes / 1024 / 1024, 1),
        "orgs": len(org_ids),
    }


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f}KB"
    if n < 1024 * 1024 * 1024:
        return f"{n/1024/1024:.1f}MB"
    return f"{n/1024/1024/1024:.2f}GB"
