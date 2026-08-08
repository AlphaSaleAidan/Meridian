"""Money Left on Table — the headline number a merchant sees on Overview.

This maths had no CI coverage. The only test of it, `src/tests/test_ai_engine.py`,
has no `test_`-prefixed functions, so pytest collects zero items from it even
under the `pytest tests src/tests` invocation docs/testing.md recommends — and
`testpaths = tests` means a bare `pytest` never looks in `src/tests` at all.

These lock the business rules that turn POS analysis into the dollar figure:
the 50% adoption haircut on pricing, $100/product/month for dead stock, the 3%
discount benchmark, and the roll-up. Getting any of them wrong misstates money
to a merchant, so they are worth pinning even though the inputs are synthetic.
"""
import pytest

from src.ai.analyzers.money_left import MoneyLeftCalculator


class _Ctx:
    """Minimal stand-in for AnalysisContext — the calculator only reads ids."""
    org_id = "00000000-0000-0000-0000-000000000000"
    location_id = None


@pytest.fixture
def calc():
    return MoneyLeftCalculator()


@pytest.fixture
def ctx():
    return _Ctx()


def _revenue(discount_rate_pct=0.0, total_revenue_cents=0, total_days=30):
    return {
        "kpis": {
            "total_revenue_cents": total_revenue_cents,
            "total_discount_cents": 0,
            "discount_rate_pct": discount_rate_pct,
            "total_days": total_days,
        }
    }


# ── Component 1: underpriced products ───────────────────────────────────

def test_pricing_opportunity_is_halved_for_adoption(calc):
    """Only half of suggested price rises are assumed to actually happen."""
    products = {
        "pricing_opportunities": [
            {"type": "price_increase", "name": "Latte",
             "estimated_monthly_impact_cents": 100_000,
             "current_price_cents": 450, "suggested_price_cents": 500},
        ]
    }
    assert calc._calc_underpriced(products)["amount_cents"] == 50_000


def test_non_price_increase_opportunities_are_excluded(calc):
    """A price *cut* is not money left on the table."""
    products = {
        "pricing_opportunities": [
            {"type": "price_decrease", "name": "Muffin",
             "estimated_monthly_impact_cents": 100_000},
        ]
    }
    result = calc._calc_underpriced(products)
    assert result["amount_cents"] == 0
    assert result["product_count"] == 0


def test_underpriced_actions_are_capped_at_five(calc):
    products = {
        "pricing_opportunities": [
            {"type": "price_increase", "name": f"Item {i}",
             "estimated_monthly_impact_cents": 1_000,
             "current_price_cents": 100, "suggested_price_cents": 120}
            for i in range(9)
        ]
    }
    result = calc._calc_underpriced(products)
    assert len(result["actions"]) == 5
    assert result["product_count"] == 9, "count reflects all, not just the listed 5"


# ── Component 2: dead stock ─────────────────────────────────────────────

def test_dead_stock_is_one_hundred_dollars_per_product(calc):
    products = {"dead_stock": [{"name": f"Item {i}"} for i in range(4)]}
    assert calc._calc_dead_stock(products)["amount_cents"] == 4 * 10_000


def test_no_dead_stock_scores_zero(calc):
    assert calc._calc_dead_stock({"dead_stock": []})["amount_cents"] == 0


# ── Component 4: discount leakage ───────────────────────────────────────

def test_discount_at_or_below_benchmark_is_not_leakage(calc):
    """3% is the documented normal rate — at the line, nothing is recoverable."""
    assert calc._calc_discount_leakage(
        _revenue(discount_rate_pct=3.0, total_revenue_cents=1_000_000)
    )["amount_cents"] == 0


def test_only_the_excess_above_three_percent_counts(calc):
    """5% on $10,000 over 30 days → the 2 points above benchmark = $200."""
    result = calc._calc_discount_leakage(
        _revenue(discount_rate_pct=5.0, total_revenue_cents=1_000_000)
    )
    assert result["amount_cents"] == 20_000
    assert result["benchmark_rate_pct"] == 3.0


def test_leakage_is_normalised_to_a_month(calc):
    """The score is per-month, so a 60-day window must halve, not double."""
    sixty = calc._calc_discount_leakage(
        _revenue(discount_rate_pct=5.0, total_revenue_cents=1_000_000, total_days=60)
    )["amount_cents"]
    assert sixty == 10_000


def test_zero_days_does_not_divide_by_zero(calc):
    calc._calc_discount_leakage(
        _revenue(discount_rate_pct=9.0, total_revenue_cents=500_000, total_days=0)
    )


# ── Roll-up ─────────────────────────────────────────────────────────────

def test_total_is_the_sum_of_every_component(calc, ctx):
    products = {
        "pricing_opportunities": [
            {"type": "price_increase", "name": "Latte",
             "estimated_monthly_impact_cents": 60_000,
             "current_price_cents": 450, "suggested_price_cents": 500},
        ],
        "dead_stock": [{"name": "Old Syrup"}, {"name": "Stale Bun"}],
    }
    result = calc.calculate(
        ctx,
        revenue=_revenue(discount_rate_pct=5.0, total_revenue_cents=1_000_000),
        products=products,
        patterns={},
    )
    expected = sum(c.get("amount_cents") or 0 for c in result["components"].values())
    assert result["total_score_cents"] == expected
    assert result["total_score_cents"] == 30_000 + 20_000 + 20_000


def test_all_five_components_are_always_present(calc, ctx):
    """The UI renders a breakdown bar per component — none may go missing."""
    result = calc.calculate(ctx, revenue=_revenue(), products={}, patterns={})
    assert set(result["components"]) == {
        "underpriced_products", "dead_stock", "peak_hour_missed",
        "discount_leakage", "staffing_waste",
    }


def test_empty_input_scores_zero_rather_than_crashing(calc, ctx):
    """A merchant who just connected their POS has nothing to analyse yet."""
    result = calc.calculate(ctx, revenue={}, products={}, patterns={})
    assert result["total_score_cents"] == 0
    assert result["top_actions"] == []


def test_top_actions_are_ranked_by_impact_and_capped(calc, ctx):
    products = {
        "pricing_opportunities": [
            {"type": "price_increase", "name": f"Item {i}",
             "estimated_monthly_impact_cents": (i + 1) * 10_000,
             "current_price_cents": 100, "suggested_price_cents": 120}
            for i in range(6)
        ],
        "dead_stock": [{"name": f"Dead {i}"} for i in range(6)],
    }
    result = calc.calculate(ctx, revenue=_revenue(), products=products, patterns={})
    impacts = [a.get("impact_cents") or 0 for a in result["top_actions"]]
    assert len(result["top_actions"]) <= 5
    assert impacts == sorted(impacts, reverse=True)


def test_every_top_action_is_attributed_to_its_component(calc, ctx):
    """MoneyLeftCard groups actions by origin — an unstamped action is orphaned."""
    products = {"dead_stock": [{"name": "Old Syrup"}]}
    result = calc.calculate(ctx, revenue=_revenue(), products=products, patterns={})
    assert result["top_actions"], "expected dead stock to produce an action"
    assert all(a.get("component") for a in result["top_actions"])


def test_result_carries_the_fields_the_frontend_reads(calc, ctx):
    """MoneyLeftScore in frontend/src/lib/api.ts depends on these keys."""
    result = calc.calculate(ctx, revenue=_revenue(), products={}, patterns={})
    for key in ("id", "total_score_cents", "components", "top_actions", "scored_at"):
        assert key in result, f"frontend reads {key}"
