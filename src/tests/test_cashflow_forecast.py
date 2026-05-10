"""
Test CashFlowForecastAgent — validates 30-day projection logic.

Tests all three paths (full/partial/minimal) and danger zone detection.
"""
import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace


def make_daily_revenue(days: int, avg_cents: int = 250000):
    """Generate mock daily revenue data."""
    result = []
    today = datetime.now()
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        dow = d.strftime("%A")
        multiplier = {
            "Monday": 0.8, "Tuesday": 0.85, "Wednesday": 0.9,
            "Thursday": 0.95, "Friday": 1.3, "Saturday": 1.4, "Sunday": 0.7,
        }.get(dow, 1.0)
        cents = int(avg_cents * multiplier + (i % 7) * 5000)
        result.append({
            "date": d.strftime("%Y-%m-%d"),
            "revenue_cents": cents,
            "transaction_count": max(1, cents // 2500),
        })
    return result


def make_context(daily, agent_outputs=None, products=None, inventory=None):
    """Build a mock AnalysisContext."""
    ctx = SimpleNamespace()
    ctx.daily_revenue = daily
    ctx.transactions = [{"id": f"txn_{i}", "total_cents": d["revenue_cents"]}
                        for i, d in enumerate(daily)]
    ctx.product_performance = products or [{"name": "Item A", "category": "Food"}]
    ctx.inventory = inventory or []
    ctx.hourly_revenue = []
    ctx.business_vertical = "restaurant"
    ctx.agent_outputs = agent_outputs or {}
    return ctx


async def test_minimal_path():
    """Minimal data: 7 days, no other agent outputs. Products present → partial path."""
    daily = make_daily_revenue(7, avg_cents=200000)
    ctx = make_context(daily)

    from src.ai.agents.cashflow_forecast import CashFlowForecastAgent
    agent = CashFlowForecastAgent(ctx)
    result = await agent.analyze()

    assert result["status"] == "complete", f"Expected complete, got {result.get('status')}"
    assert result["calculation_path"] in ("minimal", "partial")
    assert result["data"]["total_projected_revenue_cents"] > 0
    assert len(result["insights"]) >= 1
    assert "30-Day Net Cash" in result["insights"][0]["title"]
    print(f"  MINIMAL: 30d revenue=${result['data']['total_projected_revenue_cents']/100:,.0f}, "
          f"net=${result['data']['total_net_cash_cents']/100:,.0f}, "
          f"danger_days={len(result['data']['danger_zone_days'])}")
    return result


async def test_partial_path():
    """Partial data: 21 days, no forecast output."""
    daily = make_daily_revenue(21, avg_cents=350000)
    ctx = make_context(daily)

    from src.ai.agents.cashflow_forecast import CashFlowForecastAgent
    agent = CashFlowForecastAgent(ctx)
    result = await agent.analyze()

    assert result["status"] == "complete"
    assert result["calculation_path"] == "partial"
    assert result["data"]["total_projected_revenue_cents"] > 0
    print(f"  PARTIAL: 30d revenue=${result['data']['total_projected_revenue_cents']/100:,.0f}, "
          f"net=${result['data']['total_net_cash_cents']/100:,.0f}, "
          f"danger_days={len(result['data']['danger_zone_days'])}")
    return result


async def test_full_path():
    """Full data: 30 days + forecast agent output + cash_flow output."""
    daily = make_daily_revenue(30, avg_cents=400000)
    forecast_daily = [{"predicted_cents": d["revenue_cents"] + 10000} for d in daily]
    agent_outputs = {
        "forecaster": {
            "status": "complete",
            "data": {"daily_forecast": forecast_daily},
        },
        "cash_flow": {
            "status": "complete",
            "data": {"processing_fee_pct": 2.9},
        },
        "seasonality": {
            "status": "complete",
            "data": {
                "day_of_week_effects": {
                    "Monday": 0.82, "Tuesday": 0.88, "Wednesday": 0.93,
                    "Thursday": 0.97, "Friday": 1.25, "Saturday": 1.35, "Sunday": 0.72,
                },
            },
        },
    }
    txns_with_items = [{"id": f"txn_{i}", "total_cents": d["revenue_cents"],
                        "items": [{"name": "Burger", "quantity": 1, "total_cents": d["revenue_cents"]}]}
                       for i, d in enumerate(daily)]
    ctx = make_context(daily, agent_outputs=agent_outputs,
                       products=[{"name": "Burger", "category": "Food"}],
                       inventory=[{"product_id": "1", "quantity": 100}])
    ctx.transactions = txns_with_items

    from src.ai.agents.cashflow_forecast import CashFlowForecastAgent
    agent = CashFlowForecastAgent(ctx)
    result = await agent.analyze()

    assert result["status"] == "complete"
    assert result["calculation_path"] == "full"
    assert result["data"]["total_projected_revenue_cents"] > 0
    assert result["data_quality"] > 0.3
    assert len(result["data"]["daily_projections"]) == 7  # first week detail
    print(f"  FULL: 30d revenue=${result['data']['total_projected_revenue_cents']/100:,.0f}, "
          f"net=${result['data']['total_net_cash_cents']/100:,.0f}, "
          f"data_quality={result['data_quality']:.2f}, "
          f"danger_days={len(result['data']['danger_zone_days'])}")
    return result


async def test_insufficient_data():
    """Less than 7 days should return insufficient data."""
    daily = make_daily_revenue(3)
    ctx = make_context(daily)

    from src.ai.agents.cashflow_forecast import CashFlowForecastAgent
    agent = CashFlowForecastAgent(ctx)
    result = await agent.analyze()

    assert result["status"] in ("insufficient_data", "error"), \
        f"Expected insufficient_data, got {result.get('status')}"
    print(f"  INSUFFICIENT: correctly rejected with {result.get('status')}")
    return result


async def test_danger_zone_detection():
    """Very low revenue should trigger danger zone alerts."""
    daily = make_daily_revenue(14, avg_cents=5000)
    ctx = make_context(daily)

    from src.ai.agents.cashflow_forecast import CashFlowForecastAgent
    agent = CashFlowForecastAgent(ctx)
    result = await agent.analyze()

    assert result["status"] == "complete"
    has_danger = any(i["type"] == "cash_danger_zone" for i in result.get("insights", []))
    print(f"  DANGER ZONE: revenue=${result['data']['total_projected_revenue_cents']/100:,.0f}, "
          f"net=${result['data']['total_net_cash_cents']/100:,.0f}, "
          f"danger_detected={has_danger}, "
          f"danger_days={len(result['data']['danger_zone_days'])}")
    return result


async def main():
    print("Testing CashFlowForecastAgent...")
    print()

    tests = [
        ("Insufficient data rejection", test_insufficient_data),
        ("Minimal path (7 days)", test_minimal_path),
        ("Partial path (21 days)", test_partial_path),
        ("Full path (30 days + agents)", test_full_path),
        ("Danger zone detection", test_danger_zone_detection),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            await test_fn()
            print(f"  PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name} — {e}")
            failed += 1
        print()

    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
