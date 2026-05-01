"""
Scheduling Routes — Staff schedule optimization endpoints.

  POST /api/scheduling/optimize → Generate optimal staff schedule
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("meridian.api.scheduling")

router = APIRouter(prefix="/api/scheduling", tags=["scheduling"])


class OptimizeRequest(BaseModel):
    org_id: str
    num_employees: int = 8
    max_hours_per_week: int = 40
    hourly_rate_cents: int = 1500


@router.post("/optimize")
async def optimize_schedule(body: OptimizeRequest):
    """Generate an optimized staff schedule based on peak hours + staffing data."""
    from ...db import get_db
    from ...ai.engine import MeridianAI, AnalysisContext
    from ...ai.scheduling.optimizer import optimize_schedule as run_optimizer

    db = get_db()

    hourly = await db.get_hourly_revenue(body.org_id, days=30)
    if not hourly:
        raise HTTPException(status_code=400, detail="No hourly data — connect POS first")

    ctx = AnalysisContext(
        org_id=body.org_id,
        hourly_revenue=[dict(h) for h in hourly],
    )

    from ...ai.agents.peak_hours import PeakHoursAgent
    from ...ai.agents.staffing import StaffingAgent

    peak_agent = PeakHoursAgent(ctx)
    staff_agent = StaffingAgent(ctx)

    peak_result = await peak_agent.analyze()
    staff_result = await staff_agent.analyze()

    if peak_result.get("status") == "insufficient_data":
        raise HTTPException(status_code=400, detail="Need hourly data for schedule optimization")

    schedule = run_optimizer(
        peak_hours_data=peak_result,
        staffing_data=staff_result,
        num_employees=body.num_employees,
        max_hours_per_week=body.max_hours_per_week,
        hourly_rate_cents=body.hourly_rate_cents,
    )

    return {
        "org_id": body.org_id,
        "shifts": schedule.shifts,
        "total_labor_hours": schedule.total_labor_hours,
        "peak_coverage_pct": schedule.peak_coverage_pct,
        "estimated_weekly_cost_cents": schedule.estimated_cost_cents,
        "warnings": schedule.warnings,
    }
