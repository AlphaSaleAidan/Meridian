"""
E2E proof for the Clover/Toast swarm-digestion fix (PR #71).

Background
----------
`MeridianPipeline.run_full_sync()` re-fetches everything from Square before it
runs the AI swarm. After a Clover or Toast backfill there is no Square token, so
calling `run_full_sync()` either errors on the Square fetch or silently skips the
analysis — meaning a Clover/Toast merchant's data is synced to the DB but never
digested/categorized by the swarm.

`run_analysis_only()` (added in PR #71) is the fix: it skips every Square fetch
phase and runs the POS-agnostic analytics + customer-portal phases directly
against data already in the common DB schema.

These tests prove, with synthetic Clover/Toast data and no network/LLM calls:
  1. run_analysis_only() feeds the merchant's (Clover/Toast) transactions into
     the AI swarm and persists the categorized output — without ever touching
     Square.
  2. run_full_sync() DOES reach for Square (list_locations), which is exactly
     why it can't be used after a non-Square backfill.

Run:
    /root/Meridian/.venv/bin/python -m pytest tests/api/test_pipeline_analysis_only.py -v
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.live_pipeline import MeridianPipeline  # noqa: E402
from src.ai.engine import AnalysisResult  # noqa: E402


# ─── Synthetic data: a Clover (or Toast) merchant whose rows are already in
#     the common DB schema, as a real sync engine would have written them. ───
CLOVER_TXNS = [
    {"id": "clv_txn_1", "source": "clover", "total_cents": 4200,
     "created_at": "2026-06-01T12:00:00Z"},
    {"id": "clv_txn_2", "source": "clover", "total_cents": 1850,
     "created_at": "2026-06-02T13:30:00Z"},
    {"id": "clv_txn_3", "source": "clover", "total_cents": 990,
     "created_at": "2026-06-02T18:05:00Z"},
]
CLOVER_DAILY = [
    {"date": "2026-06-01", "revenue_cents": 4200, "transaction_count": 1, "avg_ticket_cents": 4200},
    {"date": "2026-06-02", "revenue_cents": 2840, "transaction_count": 2, "avg_ticket_cents": 1420},
]
CLOVER_PRODUCTS = [
    {"id": "p_latte", "name": "Latte", "category": "Beverages"},
    {"id": "p_muffin", "name": "Muffin", "category": "Bakery"},
]


def _fake_ai_result(org_id: str) -> AnalysisResult:
    """What the swarm returns after digesting the Clover data."""
    return AnalysisResult(
        org_id=org_id,
        revenue_analysis={"anomalies": [{"date": "2026-06-02", "severity": "low"}]},
        money_left_score={"total_score_cents": 9900},
        insights=[{
            "type": "category", "title": "Beverages drive 60% of revenue",
            "summary": "Latte is the top SKU.", "impact_cents": 9900,
            "confidence": 0.82, "priority": "high",
        }],
        forecasts=[{
            "forecast_type": "revenue", "period_start": "2026-06-08",
            "predicted_cents": 5200, "lower_bound": 4000, "upper_bound": 6400,
            "confidence": 0.7,
        }],
    )


def _build_mocks(org_id: str):
    """AsyncMock stand-ins for the DB, Square client, AI engine, and portal sync."""
    db = AsyncMock()
    db.select.return_value = [{"id": "loc-1", "org_id": org_id}]
    db.refresh_views.return_value = None
    db.get_daily_revenue.return_value = CLOVER_DAILY
    db.get_hourly_revenue.return_value = []
    db.get_product_performance.return_value = []
    db.get_recent_transactions.return_value = CLOVER_TXNS
    db.get_products.return_value = CLOVER_PRODUCTS
    db.save_insights.return_value = 1
    db.save_forecasts.return_value = 1
    db.save_money_left_score.return_value = None
    db.get_insights.return_value = [{
        "type": "category", "title": "Beverages drive 60% of revenue",
        "summary": "Latte is the top SKU.", "impact_cents": 9900,
    }]
    db.get_forecasts.return_value = [{
        "forecast_type": "revenue", "period_start": "2026-06-08", "predicted_cents": 5200,
    }]
    db.upsert.return_value = {"id": org_id}
    db.batch_insert.return_value = 0
    db.update_sync_status.return_value = None
    db.close.return_value = None

    square = AsyncMock()
    square.list_locations.return_value = []
    square.list_catalog.return_value = []
    square.close.return_value = None

    ai = AsyncMock()
    ai.analyze.return_value = _fake_ai_result(org_id)

    cust = AsyncMock(return_value={"success": True, "synced": True})
    return db, square, ai, cust


def _make_pipeline(org_id: str, db, square, ai, cust):
    """Construct a pipeline with all external deps patched out."""
    p = patch.multiple(
        "src.live_pipeline",
        SquareClient=lambda *a, **k: square,
        SupabaseREST=lambda *a, **k: db,
        MeridianAI=lambda *a, **k: ai,
        sync_to_customer_app=cust,
    )
    p.start()
    pipeline = MeridianPipeline(
        org_id=org_id, org_name="Synthetic Cafe", business_vertical="cafe",
        square_token="", supabase_url="http://test", supabase_key="test-key",
    )
    return pipeline, p


def test_analysis_only_digests_clover_data_without_touching_square():
    org_id = "org-clover-synthetic"
    db, square, ai, cust = _build_mocks(org_id)
    pipeline, patcher = _make_pipeline(org_id, db, square, ai, cust)
    try:
        result = asyncio.run(pipeline.run_analysis_only())
    finally:
        patcher.stop()

    # No errors
    assert result.errors == [], f"unexpected errors: {result.errors}"

    # The fix's whole point: Square is never fetched on the analysis-only path.
    square.list_locations.assert_not_called()
    square.list_catalog.assert_not_called()

    # The merchant's Clover transactions were fed into the AI swarm.
    ai.analyze.assert_awaited_once()
    context = ai.analyze.await_args.args[0]
    assert context.transactions == CLOVER_TXNS
    assert context.org_id == org_id
    assert context.business_vertical == "cafe"

    # The categorized swarm output was persisted.
    db.refresh_views.assert_awaited_once()
    db.save_insights.assert_awaited_once()
    db.save_forecasts.assert_awaited_once()

    # Insights were pushed to the customer portal.
    cust.assert_awaited_once()

    # Both POS-agnostic phases ran and reported real numbers.
    assert "analytics" in result.phases
    assert "customer_app_sync" in result.phases
    assert result.phases["analytics"]["insights"] == 1
    assert result.phases["analytics"]["forecasts"] == 1
    assert result.phases["analytics"]["money_left_score"] == 9900


def test_analysis_only_works_for_toast_merchant_too():
    """Same path, Toast-sourced rows — proves it's POS-agnostic, not Clover-specific."""
    org_id = "org-toast-synthetic"
    db, square, ai, cust = _build_mocks(org_id)
    toast_txns = [{**t, "source": "toast", "id": t["id"].replace("clv", "tst")} for t in CLOVER_TXNS]
    db.get_recent_transactions.return_value = toast_txns
    ai.analyze.return_value = _fake_ai_result(org_id)
    pipeline, patcher = _make_pipeline(org_id, db, square, ai, cust)
    try:
        result = asyncio.run(pipeline.run_analysis_only())
    finally:
        patcher.stop()

    assert result.errors == []
    square.list_locations.assert_not_called()
    ai.analyze.assert_awaited_once()
    assert ai.analyze.await_args.args[0].transactions == toast_txns
    db.save_insights.assert_awaited_once()
    cust.assert_awaited_once()


def test_full_sync_reaches_for_square_which_is_why_it_cannot_follow_a_clover_backfill():
    """Contrast test: run_full_sync() fetches Square — the bug PR #71 routes around."""
    org_id = "org-contrast"
    db, square, ai, cust = _build_mocks(org_id)
    pipeline, patcher = _make_pipeline(org_id, db, square, ai, cust)
    try:
        asyncio.run(pipeline.run_full_sync())
    finally:
        patcher.stop()

    # run_full_sync reaches for Square data. After a Clover/Toast backfill there
    # is no Square token, so this is exactly the path that must be avoided —
    # hence run_analysis_only().
    square.list_locations.assert_awaited()


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
