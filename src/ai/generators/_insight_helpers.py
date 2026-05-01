"""
Shared helpers for insight generation sub-modules.
"""
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

logger = logging.getLogger("meridian.ai.generators.insights")

try:
    from ..economics import IndustryBenchmarks
    _HAS_ECONOMICS = True
except ImportError:
    _HAS_ECONOMICS = False


def fmt_cents(cents: int) -> str:
    if abs(cents) >= 100_000:
        return f"${cents / 100:,.0f}"
    return f"${cents / 100:,.2f}"


def cite(key: str) -> str:
    if not _HAS_ECONOMICS:
        return ""
    return IndustryBenchmarks.cite(key)


def cite_detail(key: str) -> str:
    if not _HAS_ECONOMICS:
        return ""
    return IndustryBenchmarks.cite_detail(key)


MODEL_VERSION = "meridian-insight-v2.0"


def make_insight(
    ctx,
    type: str,
    title: str,
    summary: str,
    impact_cents: int = 0,
    confidence: float = 0.5,
    details: dict | None = None,
    related_products: list | None = None,
    related_categories: list | None = None,
) -> dict:
    return {
        "id": str(uuid4()),
        "org_id": ctx.org_id,
        "location_id": ctx.location_id,
        "type": type,
        "title": title,
        "summary": summary.strip(),
        "details": details or {},
        "estimated_monthly_impact_cents": impact_cents,
        "confidence_score": confidence,
        "related_products": related_products or [],
        "related_categories": related_categories or [],
        "action_status": "pending",
        "valid_until": (
            datetime.now(timezone.utc) + timedelta(days=30)
        ).isoformat(),
        "model_version": MODEL_VERSION,
        "metadata": {
            "engine": "meridian-economics-v2",
            "has_citations": bool(details and details.get("citations")),
        },
    }


def score_priority(insight: dict) -> float:
    impact = abs(insight.get("estimated_monthly_impact_cents", 0))
    confidence = insight.get("confidence_score", 0.5)
    effort = insight.get("details", {}).get("effort_to_fix", 1.0)
    if effort <= 0:
        effort = 1.0
    novelty = 1.0
    return impact * confidence * (1.0 / effort) * novelty
