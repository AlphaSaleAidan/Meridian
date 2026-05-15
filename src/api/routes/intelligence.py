"""
Financial Intelligence API — Health scores, ratios, benchmarks, and swarm evolution.

GET  /api/intelligence/health/{org_id}     -> Business health score (0-100)
GET  /api/intelligence/financial/{org_id}   -> Financial ratio analysis
GET  /api/intelligence/benchmarks/{org_id}  -> Industry benchmark comparison
GET  /api/intelligence/evolution            -> Swarm training status/metrics
POST /api/intelligence/train                -> Trigger manual training cycle
"""
import logging
import os
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import require_admin, require_service_auth

logger = logging.getLogger("meridian.api.intelligence")

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def _validate_org_id(org_id: str) -> str:
    if not _UUID_RE.match(org_id):
        raise HTTPException(422, "org_id must be a valid UUID")
    return org_id


def _get_db():
    from ...db import _db_instance

    if _db_instance is None:
        raise HTTPException(503, "Database not initialized")
    return _db_instance


def _check_feature():
    """Guard: financial intelligence must be enabled."""
    enabled = os.environ.get("ENABLE_FINANCIAL_INTELLIGENCE", "1").lower() in (
        "1",
        "true",
    )
    if not enabled:
        raise HTTPException(
            503, "Financial intelligence is disabled (ENABLE_FINANCIAL_INTELLIGENCE=0)"
        )


# ── Health Score ──────────────────────────────────────────────


@router.get("/health/{org_id}")
async def get_health_score(
    org_id: str,
    days: int = Query(30, ge=7, le=365),
    _auth=Depends(require_service_auth),
    db=Depends(_get_db),
):
    """Business health score (0-100) with grade and component breakdown."""
    _check_feature()
    org_id = _validate_org_id(org_id)

    from ...ai.financial.health_score import BusinessHealthScore

    ctx = await _load_merchant_data(db, org_id, days)
    vertical = ctx.get("business_vertical", "other")

    scorer = BusinessHealthScore(vertical)
    result = scorer.calculate(
        daily_revenue=ctx["daily_revenue"],
        transactions=ctx["transactions"],
        product_performance=ctx["products"],
        inventory=ctx.get("inventory"),
        hourly_revenue=ctx.get("hourly_revenue"),
        employee_count=ctx.get("employee_count"),
    )
    result["org_id"] = org_id
    return result


# ── Financial Ratios ──────────────────────────────────────────


@router.get("/financial/{org_id}")
async def get_financial_ratios(
    org_id: str,
    days: int = Query(30, ge=7, le=365),
    _auth=Depends(require_service_auth),
    db=Depends(_get_db),
):
    """Financial ratio analysis from POS transaction data."""
    _check_feature()
    org_id = _validate_org_id(org_id)

    from ...ai.financial.ratios import FinancialRatioAnalyzer

    ctx = await _load_merchant_data(db, org_id, days)
    vertical = ctx.get("business_vertical", "other")

    analyzer = FinancialRatioAnalyzer(vertical)
    result = analyzer.analyze(
        daily_revenue=ctx["daily_revenue"],
        transactions=ctx["transactions"],
        product_performance=ctx["products"],
        inventory=ctx.get("inventory"),
        hourly_revenue=ctx.get("hourly_revenue"),
        employee_count=ctx.get("employee_count"),
    )
    result["org_id"] = org_id
    return result


# ── Industry Benchmarks ──────────────────────────────────────


@router.get("/benchmarks/{org_id}")
async def get_benchmarks(
    org_id: str,
    days: int = Query(30, ge=7, le=365),
    _auth=Depends(require_service_auth),
    db=Depends(_get_db),
):
    """Industry benchmark comparison using NAICS sector data."""
    _check_feature()
    org_id = _validate_org_id(org_id)

    from ...ai.financial.benchmarks import PublicFinancialBenchmarks

    ctx = await _load_merchant_data(db, org_id, days)
    vertical = ctx.get("business_vertical", "other")

    bench = PublicFinancialBenchmarks(vertical)
    result = bench.compare(
        daily_revenue=ctx["daily_revenue"],
        employee_count=ctx.get("employee_count"),
    )
    result["org_id"] = org_id
    return result


# ── Swarm Evolution Status ────────────────────────────────────


@router.get("/evolution", dependencies=[Depends(require_admin)])
async def get_evolution_status():
    """Swarm training status, scorecards, and evolution metrics."""
    from ...services.training_scheduler import get_scheduler_status
    from ...ai.swarm_trainer import get_swarm_trainer

    trainer = get_swarm_trainer()
    scheduler = get_scheduler_status()
    scorecards = trainer.get_scorecards()

    return {
        "scheduler": scheduler,
        "scorecards": scorecards,
        "agent_count": len(scorecards),
        "improving": sum(1 for c in scorecards.values() if c["trend"] == "improving"),
        "degrading": sum(1 for c in scorecards.values() if c["trend"] == "degrading"),
    }


# ── Manual Training Trigger ──────────────────────────────────


class TrainRequest(BaseModel):
    org_id: str | None = None


@router.post("/train", dependencies=[Depends(require_admin)])
async def trigger_training(req: TrainRequest | None = None):
    """Trigger a manual swarm training cycle."""
    from ...services.training_scheduler import run_training_cycle

    org_id = req.org_id if req else None
    result = await run_training_cycle(org_id=org_id)
    return result


# ── Shared Data Loader ────────────────────────────────────────


async def _load_merchant_data(db, org_id: str, days: int) -> dict:
    """Load POS data for a merchant. Shared across intelligence endpoints."""
    import asyncio

    try:
        daily, hourly, products, transactions, inventory = await asyncio.gather(
            db.get_daily_revenue(org_id, days),
            db.get_hourly_revenue(org_id, days),
            db.get_product_performance(org_id, days),
            db.get_transaction_details(org_id, days),
            db.get_inventory_current(org_id),
        )
    except Exception as e:
        logger.error(f"Failed to load data for org={org_id}: {e}")
        raise HTTPException(500, f"Failed to load merchant data: {e}")

    # Determine business vertical
    vertical = "other"
    try:
        orgs = await db.query(
            "organizations",
            select="business_vertical, employee_count",
            filters={"id": f"eq.{org_id}"},
        )
        if orgs:
            vertical = orgs[0].get("business_vertical", "other") or "other"
            employee_count = orgs[0].get("employee_count")
        else:
            employee_count = None
    except Exception:
        employee_count = None

    return {
        "daily_revenue": [dict(r) for r in daily],
        "hourly_revenue": [dict(r) for r in hourly],
        "products": [dict(r) for r in products],
        "transactions": [dict(r) for r in transactions],
        "inventory": [dict(r) for r in inventory],
        "business_vertical": vertical,
        "employee_count": employee_count,
    }
