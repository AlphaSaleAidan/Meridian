"""Unit tests for the smart upsell brief (pure-function core)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.upsell_brief import (  # noqa: E402
    _norm,
    aggregate_performance,
    match_menu_item,
    render_upsell_block,
    score_candidates,
)

MENU = [
    {"name": "Cheeseburger", "price": 12.99},
    {"name": "Caesar Salad", "price": 9.99},
    {"name": "Milkshake", "price": 6.99},
    {"name": "French Fries", "price": 4.99},
    {"name": "Lobster Dinner", "price": 42.00},
]
MENU_NORMS = {_norm(m["name"]): m["name"] for m in MENU}


def _perf_row(name, revenue, qty, cost=0):
    return {"product_name": name, "total_revenue_cents": revenue,
            "total_quantity": qty, "total_cost_cents": cost}


class TestNameMatching:
    def test_exact_and_case(self):
        assert match_menu_item("cheeseburger", MENU_NORMS) == "Cheeseburger"
        assert match_menu_item("CHEESEBURGER", MENU_NORMS) == "Cheeseburger"

    def test_size_words_stripped(self):
        assert match_menu_item("Large French Fries", MENU_NORMS) == "French Fries"

    def test_containment(self):
        assert match_menu_item("Chicken Caesar Salad", MENU_NORMS) == "Caesar Salad"

    def test_fuzzy_spelling_drift(self):
        assert match_menu_item("Cheese burger", MENU_NORMS) == "Cheeseburger"

    def test_no_match(self):
        assert match_menu_item("Sushi Platter", MENU_NORMS) is None


class TestAggregation:
    def test_daily_rows_collapse(self):
        rows = [_perf_row("Milkshake", 700, 1, 100),
                _perf_row("Milkshake", 1400, 2, 200)]
        agg = aggregate_performance(rows)
        m = agg[_norm("Milkshake")]
        assert m["revenue_cents"] == 2100
        assert m["qty"] == 3
        assert m["cost_cents"] == 300

    def test_alternate_field_names(self):
        agg = aggregate_performance([
            {"name": "Fries", "revenue_cents": 500, "quantity_sold": 5}])
        assert agg[_norm("Fries")]["revenue_cents"] == 500
        assert agg[_norm("Fries")]["qty"] == 5


class TestScoring:
    def test_high_margin_flagged(self):
        # milkshake: 90% margin, decent volume
        perf = aggregate_performance(
            [_perf_row("Milkshake", 69900, 100, 6990)])
        cands = score_candidates(MENU, [], perf, [])
        names = [c["name"] for c in cands]
        assert "Milkshake" in names
        c = cands[names.index("Milkshake")]
        assert "high-margin" in c["reasons"]
        assert c["margin_pct"] == 90.0

    def test_overstock_flagged(self):
        # fries sell 1/day but 60 on hand → 60 days of stock
        perf = aggregate_performance([_perf_row("French Fries", 15000, 30)])
        inv = [{"product_name": "French Fries", "current_stock": 60}]
        cands = score_candidates(MENU, [], perf, inv)
        c = [c for c in cands if c["name"] == "French Fries"][0]
        assert "overstocked" in c["reasons"]
        assert c["days_of_stock"] == 60.0

    def test_sold_out_never_offered(self):
        perf = aggregate_performance([_perf_row("Milkshake", 69900, 100, 6990)])
        cands = score_candidates(MENU, ["Milkshake"], perf, [])
        assert all(c["name"] != "Milkshake" for c in cands)

    def test_no_reason_no_candidate(self):
        # normal margin, normal stock → nothing to push
        perf = aggregate_performance([_perf_row("Cheeseburger", 10000, 10, 6000)])
        cands = score_candidates([MENU[0]], [], perf, [])
        assert cands == []

    def test_expensive_item_downweighted(self):
        perf = aggregate_performance([
            _perf_row("Milkshake", 30000, 50, 3000),      # cheap, high margin
            _perf_row("Lobster Dinner", 168000, 40, 16800),  # pricey, high margin
        ])
        cands = score_candidates(MENU, [], perf, [])
        names = [c["name"] for c in cands]
        assert names.index("Milkshake") < names.index("Lobster Dinner")


class TestRendering:
    BRIEF = {"candidates": [
        {"name": "Milkshake", "price": 6.99, "pitch": "best margin",
         "reasons": ["high-margin"]}]}

    def test_none_mode_empty(self):
        assert render_upsell_block(self.BRIEF, "none") == ""

    def test_missing_brief_empty(self):
        assert render_upsell_block(None, "gentle") == ""
        assert render_upsell_block({"candidates": []}, "gentle") == ""

    def test_gentle_renders_one_max(self):
        block = render_upsell_block(self.BRIEF, "gentle")
        assert "Milkshake ($6.99)" in block
        assert "ONE suggestion max" in block
        assert block.startswith("\n\nTODAY'S UPSELL PRIORITIES")

    def test_active_allows_two(self):
        assert "TWO suggestions max" in render_upsell_block(self.BRIEF, "active")


# ── owner brain ──────────────────────────────────────────────────────────────

from src.services.owner_brain import (  # noqa: E402
    current_daypart,
    daypart_for_hour,
    mine_dayparts,
    mine_pairings,
)


def _txn_item(tid, name, at="2026-08-01T18:30:00+00:00", qty=1):
    return {"transaction_id": tid, "product_name": name,
            "transaction_at": at, "quantity": qty}


class TestPairings:
    def test_attach_rate_mined(self):
        rows = []
        # 10 burger orders, 6 with shake, 2 with fries
        for i in range(10):
            rows.append(_txn_item(f"t{i}", "Burger"))
            if i < 6:
                rows.append(_txn_item(f"t{i}", "Shake"))
            if i < 2:
                rows.append(_txn_item(f"t{i}", "Fries"))
        p = mine_pairings(rows, min_support=5)
        burger = p["Burger"]
        assert burger[0]["partner"] == "Shake"
        assert burger[0]["attach_pct"] == 60.0
        # fries at 20% clears the 15% floor and ranks second
        assert burger[1]["partner"] == "Fries"

    def test_low_support_item_excluded(self):
        rows = [_txn_item("t1", "Caviar"), _txn_item("t1", "Champagne")]
        assert mine_pairings(rows, min_support=5) == {}

    def test_weak_attach_excluded(self):
        rows = []
        for i in range(20):
            rows.append(_txn_item(f"t{i}", "Burger"))
        rows.append(_txn_item("t0", "Pickle"))  # 5% attach
        assert "Burger" not in mine_pairings(rows, min_support=5)


class TestDayparts:
    def test_hour_buckets(self):
        assert daypart_for_hour(8) == "morning"
        assert daypart_for_hour(12) == "lunch"
        assert daypart_for_hour(19) == "dinner"
        assert daypart_for_hour(23) == "late-night"
        assert daypart_for_hour(2) == "late-night"

    def test_items_bucketed_by_local_hour(self):
        rows = [
            _txn_item("t1", "Croissant", at="2026-08-01T08:00:00+00:00"),
            _txn_item("t2", "Croissant", at="2026-08-02T09:00:00+00:00"),
            _txn_item("t3", "Steak", at="2026-08-01T19:00:00+00:00"),
        ]
        dp = mine_dayparts(rows, tz_name="")
        assert dp["morning"] == ["Croissant"]
        assert dp["dinner"] == ["Steak"]

    def test_current_daypart_returns_known_bucket(self):
        assert current_daypart("") in {
            "morning", "lunch", "afternoon", "dinner", "late-night"}


class TestOwnerBrainRendering:
    BRIEF = {
        "candidates": [{"name": "Milkshake", "price": 6.99,
                        "pitch": "best margin", "reasons": ["high-margin"]}],
        "pairings": {"Burger": [{"partner": "Milkshake", "attach_pct": 42.0}]},
        "dayparts": {dp: ["Milkshake"] for dp in
                     ("morning", "lunch", "afternoon", "dinner", "late-night")},
    }

    def test_pairings_rendered(self):
        block = render_upsell_block(self.BRIEF, "gentle")
        assert "Order has Burger" in block
        assert "42% of Burger orders" in block

    def test_daypart_line_rendered(self):
        block = render_upsell_block(self.BRIEF, "gentle")
        assert "RIGHT NOW (" in block

    def test_pairings_alone_still_render(self):
        block = render_upsell_block(
            {"candidates": [], "pairings": self.BRIEF["pairings"]}, "gentle")
        assert "PAIRINGS" in block
        assert "TODAY'S UPSELL PRIORITIES" not in block

    def test_none_mode_still_suppresses_everything(self):
        assert render_upsell_block(self.BRIEF, "none") == ""
