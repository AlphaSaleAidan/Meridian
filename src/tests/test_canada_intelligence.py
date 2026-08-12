"""Regression tests for the Canada intelligence overlay wiring.

Guards two things: a Canadian merchant actually receives the overlay + merged
insights, and a US merchant passes through completely unchanged (the overlay must
never touch non-Canadian analyses).
"""
import asyncio

from src.ai.engine import AnalysisContext, AnalysisResult
from src.ai.canada.engine_hook import apply_canada_intelligence


def _result(org_id: str) -> AnalysisResult:
    r = AnalysisResult(org_id=org_id)
    r.revenue_analysis = {"kpis": {"avg_ticket_cents": 4200, "avg_daily_revenue_cents": 380000}}
    r.money_left_score = {"total_score_cents": 120000}
    r.insights = [{"id": "base-1", "title": "baseline insight"}]
    return r


def test_canadian_merchant_gets_overlay_and_insights():
    ctx = AnalysisContext(
        org_id="org-ca", timezone="America/Toronto", province="ON",
        currency="CAD", business_vertical="restaurant",
    )
    r = asyncio.run(apply_canada_intelligence(_result("org-ca"), ctx))
    assert r.canada_overlay is not None
    assert len(r.insights) > 1  # baseline + injected canada insights
    assert r.summary["canada_overlay"] is True
    assert any("canada" in (i.get("tags") or []) for i in r.insights)


def test_us_merchant_passes_through_unchanged():
    ctx = AnalysisContext(
        org_id="org-us", timezone="America/Los_Angeles",
        currency="USD", business_vertical="restaurant",
    )
    r = asyncio.run(apply_canada_intelligence(_result("org-us"), ctx))
    assert r.canada_overlay is None
    assert len(r.insights) == 1
    assert r.summary["canada_overlay"] is False


def test_detection_by_currency_alone():
    # No province, US-looking timezone, but CAD currency → still Canadian.
    ctx = AnalysisContext(org_id="org-ca2", timezone="America/Los_Angeles", currency="CAD")
    r = asyncio.run(apply_canada_intelligence(_result("org-ca2"), ctx))
    assert r.canada_overlay is not None
