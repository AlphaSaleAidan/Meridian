"""
Predictive Engine API Routes.

Endpoints:
  POST /api/predictive/scenario         → What-if scenario engine
  GET  /api/predictive/churn/{org_id}   → Churn early warning
  GET  /api/predictive/pricing/{org_id} → Dynamic pricing optimizer
  GET  /api/predictive/demand/{org_id}  → Per-product demand forecast
  GET  /api/predictive/goals/{org_id}   → Revenue goal tracker
  GET  /api/predictive/root-cause/{org_id} → Root cause analyzer
  GET  /api/predictive/alerts/{org_id}  → Evaluate all alerts
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("meridian.api.predictive")

router = APIRouter(prefix="/api/predictive", tags=["predictive"])


class ScenarioRequest(BaseModel):
    org_id: str
    scenario_type: str
    params: dict


async def _load_ctx_and_outputs(org_id: str, days: int = 30):
    """Load AnalysisContext and run agent swarm for predictive engines."""
    import asyncio as _asyncio

    from ...db import get_db
    from ...ai.engine import AnalysisContext, run_agent_swarm

    db = get_db()

    # SupabaseREST uses .select(); SupabaseDB uses direct query methods
    if hasattr(db, "get_daily_revenue"):
        # get_recent_transactions is the correct method name in SupabaseREST
        # (get_transaction_details does not exist)
        _get_transactions = getattr(db, "get_transaction_details", None) or getattr(db, "get_recent_transactions", None)
        _get_inventory = getattr(db, "get_inventory_current", None)

        daily, hourly, products = await _asyncio.gather(
            db.get_daily_revenue(org_id, days),
            db.get_hourly_revenue(org_id, days),
            db.get_product_performance(org_id, days),
        )

        # Fetch transactions and inventory with graceful fallback
        transactions = []
        inventory = []
        if _get_transactions:
            try:
                transactions = await _get_transactions(org_id, days)
            except Exception as e:
                logger.warning(f"Failed to load transactions: {e}")
        else:
            # Fallback: use SupabaseREST.select() directly
            try:
                from datetime import datetime, timezone, timedelta
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                transactions = await db.select(
                    "transactions",
                    filters={
                        "org_id": f"eq.{org_id}",
                        "transaction_at": f"gte.{cutoff}",
                    },
                    order="transaction_at.desc",
                    limit=5000,
                )
            except Exception as e:
                logger.warning(f"Fallback transactions query failed: {e}")

        if _get_inventory:
            try:
                inventory = await _get_inventory(org_id)
            except Exception as e:
                logger.warning(f"Failed to load inventory: {e}")
        else:
            # Fallback: use SupabaseREST.select() directly
            try:
                inventory = await db.select(
                    "inventory",
                    filters={"org_id": f"eq.{org_id}"},
                )
            except Exception as e:
                logger.warning(f"Fallback inventory query failed: {e}")
    else:
        daily = hourly = products = transactions = inventory = []

    ctx = AnalysisContext(
        org_id=org_id,
        analysis_days=days,
        daily_revenue=[dict(r) for r in daily] if daily else [],
        hourly_revenue=[dict(r) for r in hourly] if hourly else [],
        product_performance=[dict(r) for r in products] if products else [],
        transactions=[dict(r) for r in transactions] if transactions else [],
        inventory=[dict(r) for r in inventory] if inventory else [],
    )

    try:
        ctx.agent_outputs = await run_agent_swarm(ctx)
    except Exception as e:
        logger.warning(f"Agent swarm failed for predictive: {e}")
        ctx.agent_outputs = {}

    return ctx


@router.post("/scenario")
async def run_scenario(req: ScenarioRequest):
    """Run a what-if scenario (price_change, add_shift, drop_products)."""
    from ...ai.predictive.scenario_engine import ScenarioEngine

    ctx = await _load_ctx_and_outputs(req.org_id)
    engine = ScenarioEngine(ctx)
    result = await engine.run(req.scenario_type, req.params)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Scenario failed"))
    return result


@router.get("/churn/{org_id}")
async def get_churn_warning(org_id: str, days: int = Query(90, ge=14, le=365)):
    """Customer churn early warning system."""
    from ...ai.predictive.churn_warning import ChurnWarningAgent

    ctx = await _load_ctx_and_outputs(org_id, days)
    agent = ChurnWarningAgent(ctx)
    return await agent.analyze()


@router.get("/pricing/{org_id}")
async def get_dynamic_pricing(org_id: str, days: int = Query(30, ge=7, le=90)):
    """Dynamic pricing optimization recommendations."""
    from ...ai.predictive.dynamic_pricing import DynamicPricingOptimizer

    ctx = await _load_ctx_and_outputs(org_id, days)
    optimizer = DynamicPricingOptimizer(ctx)
    return await optimizer.analyze()


@router.get("/demand/{org_id}")
async def get_demand_forecast(org_id: str, days: int = Query(30, ge=7, le=90)):
    """Per-product demand forecast with prep guides."""
    from ...ai.predictive.demand_forecast import DemandForecastAgent

    ctx = await _load_ctx_and_outputs(org_id, days)
    agent = DemandForecastAgent(ctx)
    return await agent.analyze()


@router.get("/goals/{org_id}")
async def get_goal_tracker(
    org_id: str,
    goal_cents: Optional[int] = Query(None, description="Monthly revenue goal in cents"),
):
    """Revenue goal tracker with daily countdown."""
    from ...ai.predictive.goal_tracker import GoalTrackerAgent

    ctx = await _load_ctx_and_outputs(org_id)
    agent = GoalTrackerAgent(ctx)
    return await agent.analyze(monthly_goal_cents=goal_cents)


@router.get("/root-cause/{org_id}")
async def get_root_cause(
    org_id: str,
    metric: str = Query("revenue", description="Metric to analyze"),
    change_pct: Optional[float] = Query(None, description="Override change %"),
):
    """Root cause analysis for metric changes."""
    from ...ai.predictive.root_cause import RootCauseAnalyzer

    ctx = await _load_ctx_and_outputs(org_id)
    analyzer = RootCauseAnalyzer(ctx)
    return await analyzer.analyze(metric_name=metric, change_pct=change_pct)


@router.get("/alerts/{org_id}")
async def get_alerts(org_id: str, days: int = Query(30, ge=7, le=90)):
    """Evaluate all alert rules and return any fired alerts."""
    from ...ai.alerts import ALL_ALERTS

    ctx = await _load_ctx_and_outputs(org_id, days)
    all_fired = []
    for alert_cls in ALL_ALERTS:
        try:
            alert = alert_cls(ctx, agent_outputs=ctx.agent_outputs)
            fired = await alert.evaluate()
            all_fired.extend(fired)
        except Exception as e:
            logger.error(f"Alert {alert_cls.__name__} failed: {e}")

    all_fired.sort(
        key=lambda a: {"urgent": 0, "critical": 1, "warning": 2, "info": 3}.get(
            a.get("severity", "info"), 4
        )
    )
    return {"org_id": org_id, "alerts": all_fired, "total": len(all_fired)}
