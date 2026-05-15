"""
Cold Storage Archives API Routes.

Endpoints:
  GET    /api/archives/                  -> List all archives
  GET    /api/archives/stats             -> Storage statistics
  GET    /api/archives/tiers             -> Tier definitions & table mapping
  GET    /api/archives/{org_id}          -> List archives for an org
  GET    /api/archives/{org_id}/{year}/{month}/{table} -> Read archived data
  POST   /api/archives/{org_id}/{year}/{month}         -> Trigger manual archive
  POST   /api/archives/{org_id}/{year}/{month}/upload  -> Upload to R2
"""
import logging

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger("meridian.api.archives")

router = APIRouter(prefix="/api/archives", tags=["archives"])


@router.get("/tiers")
async def list_tiers():
    from ...workers.cold_storage import ARCHIVE_TIERS
    tiers = {}
    total_tables = 0
    for tier_name, tier in ARCHIVE_TIERS.items():
        tables = [t["table"] for t in tier["tables"]]
        tiers[tier_name] = {
            "label": tier["label"],
            "resale_tier": tier["resale_tier"],
            "table_count": len(tables),
            "tables": tables,
        }
        total_tables += len(tables)
    return {"total_tiers": len(tiers), "total_tables": total_tables, "tiers": tiers}


@router.get("/stats")
async def archive_stats():
    from ...workers.cold_storage import get_archive_stats
    return get_archive_stats()


@router.get("/")
async def list_all_archives():
    from ...workers.cold_storage import list_archives
    return {"archives": list_archives()}


@router.get("/{org_id}")
async def list_org_archives(org_id: str):
    from ...workers.cold_storage import list_archives
    return {"org_id": org_id, "archives": list_archives(org_id)}


@router.get("/{org_id}/{year}/{month}/{table}")
async def read_archived_data(
    org_id: str,
    year: int,
    month: int,
    table: str,
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
):
    from ...workers.cold_storage import read_archive

    rows = read_archive(org_id, year, month, table)
    if not rows:
        raise HTTPException(status_code=404, detail="Archive not found")

    total = len(rows)
    sliced = rows[offset : offset + limit]
    return {
        "org_id": org_id,
        "period": f"{year}-{month:02d}",
        "table": table,
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": sliced,
    }


@router.post("/{org_id}/{year}/{month}")
async def trigger_archive(org_id: str, year: int, month: int):
    from ...workers.tasks import archive_org_month_task

    task = archive_org_month_task.apply_async(args=[org_id, year, month])
    return {
        "status": "queued",
        "task_id": task.id,
        "org_id": org_id,
        "period": f"{year}-{month:02d}",
    }


@router.post("/{org_id}/{year}/{month}/upload")
async def trigger_r2_upload(org_id: str, year: int, month: int):
    from ...workers.tasks import upload_archive_to_r2

    task = upload_archive_to_r2.apply_async(args=[org_id, year, month])
    return {
        "status": "queued",
        "task_id": task.id,
        "org_id": org_id,
        "period": f"{year}-{month:02d}",
    }
