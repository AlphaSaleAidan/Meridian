"""
BentoML Service — Serve top 5 AI agents as HTTP endpoints.

Endpoints:
  POST /predict/forecast   — Revenue forecast (7/14/30 day)
  POST /predict/anomaly    — Anomaly detection on recent data
  POST /predict/churn      — Customer churn risk scoring
  POST /predict/pricing    — Dynamic pricing recommendations
  POST /predict/staffing   — Staffing optimization
"""
import logging
from typing import Any

import bentoml
from pydantic import BaseModel

logger = logging.getLogger("meridian.serving")


class PredictRequest(BaseModel):
    org_id: str
    data: dict[str, Any]
    days: int = 30


class PredictResponse(BaseModel):
    org_id: str
    agent: str
    status: str
    result: dict[str, Any]
    duration_ms: float


@bentoml.service(
    name="meridian-ai",
    traffic={"timeout": 120},
    resources={"cpu": "2", "memory": "4Gi"},
)
class MeridianService:
    def __init__(self):
        from ..ai.engine import AnalysisContext
        self._context_cls = AnalysisContext

    def _build_context(self, req: PredictRequest) -> Any:
        return self._context_cls(
            org_id=req.org_id,
            daily_revenue=req.data.get("daily_revenue", []),
            hourly_revenue=req.data.get("hourly_revenue", []),
            product_performance=req.data.get("product_performance", []),
            transactions=req.data.get("transactions", []),
            inventory=req.data.get("inventory", []),
            analysis_days=req.days,
        )

    @bentoml.api
    async def forecast(self, req: PredictRequest) -> PredictResponse:
        """Revenue forecast using ForecasterAgent."""
        import time
        start = time.monotonic()

        ctx = self._build_context(req)
        from ..ai.agents.forecaster import ForecasterAgent
        agent = ForecasterAgent(ctx)
        result = await agent.analyze()

        return PredictResponse(
            org_id=req.org_id,
            agent="forecaster",
            status="complete",
            result=result if isinstance(result, dict) else {"output": str(result)},
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )

    @bentoml.api
    async def anomaly(self, req: PredictRequest) -> PredictResponse:
        """Anomaly detection using RevenueTrendAgent."""
        import time
        start = time.monotonic()

        ctx = self._build_context(req)
        from ..ai.agents.revenue_trend import RevenueTrendAgent
        agent = RevenueTrendAgent(ctx)
        result = await agent.analyze()

        return PredictResponse(
            org_id=req.org_id,
            agent="revenue_trend",
            status="complete",
            result=result if isinstance(result, dict) else {"output": str(result)},
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )

    @bentoml.api
    async def churn(self, req: PredictRequest) -> PredictResponse:
        """Customer churn risk scoring using CustomerLTVAgent."""
        import time
        start = time.monotonic()

        ctx = self._build_context(req)
        from ..ai.agents.customer_ltv import CustomerLTVAgent
        agent = CustomerLTVAgent(ctx)
        result = await agent.analyze()

        return PredictResponse(
            org_id=req.org_id,
            agent="customer_ltv",
            status="complete",
            result=result if isinstance(result, dict) else {"output": str(result)},
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )

    @bentoml.api
    async def pricing(self, req: PredictRequest) -> PredictResponse:
        """Dynamic pricing recommendations using PricingPowerAgent."""
        import time
        start = time.monotonic()

        ctx = self._build_context(req)
        from ..ai.agents.pricing_power import PricingPowerAgent
        agent = PricingPowerAgent(ctx)
        result = await agent.analyze()

        return PredictResponse(
            org_id=req.org_id,
            agent="pricing_power",
            status="complete",
            result=result if isinstance(result, dict) else {"output": str(result)},
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )

    @bentoml.api
    async def staffing(self, req: PredictRequest) -> PredictResponse:
        """Staffing optimization using StaffingAgent."""
        import time
        start = time.monotonic()

        ctx = self._build_context(req)
        from ..ai.agents.staffing import StaffingAgent
        agent = StaffingAgent(ctx)
        result = await agent.analyze()

        return PredictResponse(
            org_id=req.org_id,
            agent="staffing",
            status="complete",
            result=result if isinstance(result, dict) else {"output": str(result)},
            duration_ms=round((time.monotonic() - start) * 1000, 1),
        )
