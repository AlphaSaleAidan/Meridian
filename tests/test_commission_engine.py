"""
Canada commission engine — exact-dollar unit tests.

RED-FIRST tests for src/services/commission_engine.py, the replacement for the
dead percentage-based commission system (commissions table: 0 rows ever;
billing.py / stripe_checkout.py insert columns that don't exist).

Source of truth: the official Rep Commission One-Pager.
Every package's total commission splits across 4 milestones in fixed
57-unit weights: M0=13, M1=28, M2=10, M3=6.
payout(package, milestone) = unit_value(package) x weight(milestone).

All money is INTEGER CENTS. All assertions are exact.
"""

from datetime import date

import pytest

from src.services.commission_engine import (
    DEFAULT_PACKAGES,
    MILESTONE_WEIGHTS,
    CommissionEngineService,
    EngineConfig,
    Package,
    add_months,
    adjusted_m0_cents,
    compute_schedule,
    first_friday,
    m0_pay_date,
    milestone_amounts,
    next_settlement_date,
    package_total_cents,
    post_close_upsell_cents,
)

# ───────────────────────────────────────────────────────────────────────────
# 1. The 4x4 milestone value matrix + totals (EXACT, from the One-Pager)
# ───────────────────────────────────────────────────────────────────────────

# package_key -> (list_monthly_cents, unit_cents, M0, M1, M2, M3, total)
MATRIX = {
    "minimum": (20000, 600, 7800, 16800, 6000, 3600, 34200),    # $78.00/$168.00/$60.00/$36.00 = $342.00
    "starter": (25000, 750, 9750, 21000, 7500, 4500, 42750),    # $97.50/$210.00/$75.00/$45.00 = $427.50
    "middle": (39900, 1375, 17875, 38500, 13750, 8250, 78375),  # $178.75/$385.00/$137.50/$82.50 = $783.75
    "higher": (68900, 2000, 26000, 56000, 20000, 12000, 114000),  # $260.00/$560.00/$200.00/$120.00 = $1,140.00
}


def test_weights_are_the_57_unit_split():
    assert MILESTONE_WEIGHTS == {"M0": 13, "M1": 28, "M2": 10, "M3": 6}
    assert sum(MILESTONE_WEIGHTS.values()) == 57


@pytest.mark.parametrize("key", list(MATRIX))
def test_default_packages_match_one_pager(key):
    list_cents, unit_cents, *_ = MATRIX[key]
    pkg = DEFAULT_PACKAGES[key]
    assert pkg.list_monthly_cents == list_cents
    assert pkg.unit_value_cents == unit_cents


@pytest.mark.parametrize("key", list(MATRIX))
def test_milestone_amounts_exact(key):
    _, _, m0, m1, m2, m3, total = MATRIX[key]
    amounts = milestone_amounts(DEFAULT_PACKAGES[key])
    assert amounts == {"M0": m0, "M1": m1, "M2": m2, "M3": m3}
    assert package_total_cents(DEFAULT_PACKAGES[key]) == total
    assert sum(amounts.values()) == total


# ───────────────────────────────────────────────────────────────────────────
# 2. M0 adjustments (M0 only; M1/M2/M3 never adjusted)
# ───────────────────────────────────────────────────────────────────────────

CFG = EngineConfig()  # defaults: anchor=True, floor=True, CAD, retro=False


def test_upsell_adds_half_the_delta_to_m0():
    # Starter negotiated $300 vs list $250 -> M0 += 0.50 x $50 = +$25.00
    assert adjusted_m0_cents(DEFAULT_PACKAGES["starter"], 30000, CFG) == 9750 + 2500


def test_upsell_middle_package():
    # Middle negotiated $449 vs list $399 -> +$25.00
    assert adjusted_m0_cents(DEFAULT_PACKAGES["middle"], 44900, CFG) == 17875 + 2500


def test_upsell_odd_delta_floors_the_half_cent():
    # Delta of 1 cent -> 0.5 cents -> floors to 0 (documented; flagged for Aidan)
    assert adjusted_m0_cents(DEFAULT_PACKAGES["starter"], 25001, CFG) == 9750


def test_discount_subtracts_full_delta_from_m0():
    # Middle negotiated $374 vs list $399 (both above the $250 floor) -> M0 -= $25.00
    assert adjusted_m0_cents(DEFAULT_PACKAGES["middle"], 37400, CFG) == 17875 - 2500


def test_no_adjustment_at_list_price():
    for key in MATRIX:
        pkg = DEFAULT_PACKAGES[key]
        assert adjusted_m0_cents(pkg, pkg.list_monthly_cents, CFG) == MATRIX[key][2]


def test_m0_floors_at_zero_by_default():
    # Higher discounted to the $200 floor -> 26000 - 48900 = -22900 -> floored to 0
    assert adjusted_m0_cents(DEFAULT_PACKAGES["higher"], 20000, CFG) == 0


def test_m0_floor_disabled_allows_negative():
    cfg = EngineConfig(m0_floor_zero=False)
    assert adjusted_m0_cents(DEFAULT_PACKAGES["higher"], 20000, cfg) == -22900


def test_m1_m2_m3_never_adjusted():
    # Big upsell on Starter: M0 moves, later milestones do not.
    rows = compute_schedule(
        package_key="starter",
        negotiated_monthly_cents=30000,
        close_date=date(2026, 7, 21),
        activation_date=date(2026, 7, 21),
        config=CFG,
    )
    by_ms = {r.milestone: r.amount_cents for r in rows}
    assert by_ms["M0"] == 9750 + 2500
    assert by_ms["M1"] == 21000
    assert by_ms["M2"] == 7500
    assert by_ms["M3"] == 4500


# ───────────────────────────────────────────────────────────────────────────
# 3. $200 USD floor — the minimum-price tier; reps cannot sell below it
# ───────────────────────────────────────────────────────────────────────────

def test_four_packages_lowest_is_200():
    assert set(DEFAULT_PACKAGES) == {"minimum", "starter", "middle", "higher"}
    assert min(p.list_monthly_cents for p in DEFAULT_PACKAGES.values()) == 20000


def test_discount_cannot_price_below_200_floor():
    # A "discount" to $150 is clamped to the $200 floor. On minimum ($200 list)
    # that means no adjustment at all -> M0 stays $78.00.
    assert adjusted_m0_cents(DEFAULT_PACKAGES["minimum"], 15000, CFG) == 7800


def test_starter_discount_clamps_at_200_floor():
    # Starter ($250) sold at $150 clamps to $200 -> delta -$50 -> M0 9750 - 5000.
    assert adjusted_m0_cents(DEFAULT_PACKAGES["starter"], 15000, CFG) == 9750 - 5000


def test_non_floor_discount_still_applies():
    # Middle discounted to $349 (above floor) -> -$50 off M0.
    assert adjusted_m0_cents(DEFAULT_PACKAGES["middle"], 34900, CFG) == 17875 - 5000


# ───────────────────────────────────────────────────────────────────────────
# 4. M0 pay-date: Friday of the week AFTER — always a full payroll week
#    between close and pay (>= 7 days), so the immediate Friday is skipped.
#    July 2026: Mon 20, Tue 21, ... Fri 24, Sat 25, Sun 26, Fri 31, Fri Aug 7.
# ───────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "close,expected",
    [
        (date(2026, 7, 21), date(2026, 7, 31)),  # Tuesday -> NEXT Friday, not Jul 24
        (date(2026, 7, 23), date(2026, 7, 31)),  # Thursday -> skips next-day Friday
        (date(2026, 7, 24), date(2026, 7, 31)),  # Friday close -> a full week later
        (date(2026, 7, 25), date(2026, 8, 7)),   # Saturday -> Jul 31 is only 6 days out
        (date(2026, 7, 26), date(2026, 8, 7)),   # Sunday -> Jul 31 is only 5 days out
        (date(2026, 7, 20), date(2026, 7, 31)),  # Monday
    ],
)
def test_m0_pay_date(close, expected):
    assert m0_pay_date(close) == expected


def test_m0_pay_date_is_always_a_friday_and_at_least_a_week_out():
    d = date(2026, 1, 1)
    for offset in range(0, 60):
        close = date.fromordinal(d.toordinal() + offset)
        pay = m0_pay_date(close)
        assert pay.weekday() == 4  # Friday
        assert (pay - close).days >= 7


# ───────────────────────────────────────────────────────────────────────────
# 5. Month math + quarterly settlement mapping
#    Default settlement dates: first Friday of Jan/Apr/Jul/Oct
#    (PARAMETERIZED in config — flagged for Aidan sign-off).
# ───────────────────────────────────────────────────────────────────────────

def test_add_months_clamps_short_months():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2025, 10, 31), 4) == date(2026, 2, 28)
    assert add_months(date(2026, 5, 31), 4) == date(2026, 9, 30)
    assert add_months(date(2026, 1, 15), 12) == date(2027, 1, 15)


def test_first_friday():
    assert first_friday(2026, 1) == date(2026, 1, 2)
    assert first_friday(2026, 4) == date(2026, 4, 3)
    assert first_friday(2026, 7) == date(2026, 7, 3)
    assert first_friday(2026, 10) == date(2026, 10, 2)
    assert first_friday(2027, 1) == date(2027, 1, 1)  # Jan 1 2027 is a Friday


def test_next_settlement_strictly_after_earning():
    cfg = EngineConfig()
    assert next_settlement_date(date(2026, 2, 10), cfg) == date(2026, 4, 3)
    # Earned ON a settlement date -> paid on the NEXT one (strictly after)
    assert next_settlement_date(date(2026, 4, 3), cfg) == date(2026, 7, 3)
    assert next_settlement_date(date(2026, 12, 15), cfg) == date(2027, 1, 1)


def test_settlement_months_are_parameterized():
    cfg = EngineConfig(settlement_months=(2, 5, 8, 11))
    # first Friday of May 2026: May 1 2026 is a Friday
    assert next_settlement_date(date(2026, 3, 1), cfg) == date(2026, 5, 1)


# ───────────────────────────────────────────────────────────────────────────
# 6. Full schedule: statuses, earned dates (months 4/9/12), payable dates
# ───────────────────────────────────────────────────────────────────────────

def test_full_schedule_starter_at_list():
    rows = compute_schedule(
        package_key="starter",
        negotiated_monthly_cents=25000,
        close_date=date(2026, 7, 21),       # Tuesday
        activation_date=date(2026, 7, 21),
        config=CFG,
    )
    assert [r.milestone for r in rows] == ["M0", "M1", "M2", "M3"]

    m0, m1, m2, m3 = rows
    # M0: earned at close, paid the Friday after a full payroll week
    assert m0.amount_cents == 9750
    assert m0.status == "earned"
    assert m0.earned_at == date(2026, 7, 21)
    assert m0.payable_on == date(2026, 7, 31)

    # M1/M2/M3: earned at months 4/9/12 of activity, paid next settlement after
    assert m1.status == "pending"
    assert m1.earned_at == date(2026, 11, 21)
    assert m1.payable_on == date(2027, 1, 1)   # first Friday Jan 2027

    assert m2.status == "pending"
    assert m2.earned_at == date(2027, 4, 21)
    assert m2.payable_on == date(2027, 7, 2)   # first Friday Jul 2027

    assert m3.status == "pending"
    assert m3.earned_at == date(2027, 7, 21)
    assert m3.payable_on == date(2027, 10, 1)  # first Friday Oct 2027

    # classification metadata: independent-contractor, lump-sum, outcome-based
    for r in rows:
        assert r.currency == "CAD"
        assert r.classification == "independent_contractor_lump_sum_outcome_based"


# ───────────────────────────────────────────────────────────────────────────
# 7. Retro upsell flag (default: post-close upsells earn nothing)
# ───────────────────────────────────────────────────────────────────────────

def test_retro_upsell_off_by_default():
    assert post_close_upsell_cents(25000, 30000, EngineConfig()) == 0


def test_retro_upsell_on_pays_half_the_delta():
    cfg = EngineConfig(retro_upsell_commission=True)
    assert post_close_upsell_cents(25000, 30000, cfg) == 2500


# ───────────────────────────────────────────────────────────────────────────
# 8. Service: idempotency + cancellation halting (fake db, no I/O in math)
# ───────────────────────────────────────────────────────────────────────────

class FakeDB:
    """In-memory stand-in for SupabaseREST enforcing UNIQUE(account_id, milestone)."""

    def __init__(self):
        self.rows: list[dict] = []

    async def upsert(self, table, data, on_conflict="", return_data=True,
                     ignore_duplicates=False):
        assert table == "commission_milestones"
        assert on_conflict == "account_id,milestone"
        assert ignore_duplicates is True  # ON CONFLICT DO NOTHING semantics
        data = data if isinstance(data, list) else [data]
        inserted = []
        for row in data:
            key = (row["account_id"], row["milestone"])
            if any((r["account_id"], r["milestone"]) == key for r in self.rows):
                continue  # duplicate: first write wins
            self.rows.append(dict(row))
            inserted.append(dict(row))
        return inserted

    async def update(self, table, data, filters):
        assert table == "commission_milestones"
        updated = []
        for row in self.rows:
            if all(row.get(col) == val.removeprefix("eq.")
                   for col, val in filters.items()):
                row.update(data)
                updated.append(dict(row))
        return updated

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        out = []
        for row in self.rows:
            if all(row.get(col) == val.removeprefix("eq.")
                   for col, val in (filters or {}).items()):
                out.append(dict(row))
        return out


@pytest.fixture
def svc():
    return CommissionEngineService(db=FakeDB(), config=EngineConfig())


ACCOUNT = "org-1111"
REP = "rep-2222"


async def _schedule(svc, account_id=ACCOUNT):
    return await svc.schedule_account(
        account_id=account_id,
        rep_id=REP,
        package_key="starter",
        negotiated_monthly_cents=25000,
        close_date=date(2026, 7, 21),
    )


async def test_schedule_account_writes_four_milestones(svc):
    rows = await _schedule(svc)
    assert len(rows) == 4
    assert {r["milestone"] for r in rows} == {"M0", "M1", "M2", "M3"}
    assert sum(r["amount_cents"] for r in rows) == 42750
    assert all(r["currency"] == "CAD" for r in rows)


async def test_schedule_account_is_idempotent(svc):
    await _schedule(svc)
    second = await _schedule(svc)  # double-insert same milestones = no-op
    assert second == []
    assert len(svc.db.rows) == 4


async def test_cancel_account_halts_only_future_milestones(svc):
    await _schedule(svc)
    halted = await svc.cancel_account(ACCOUNT)
    # M0 was earned at close -> untouched. M1/M2/M3 pending -> halted.
    assert halted == 3
    statuses = {r["milestone"]: r["status"] for r in svc.db.rows}
    assert statuses == {"M0": "earned", "M1": "halted", "M2": "halted", "M3": "halted"}


async def test_cancel_never_claws_back_paid(svc):
    await _schedule(svc)
    await svc.db.update(
        "commission_milestones",
        {"status": "paid"},
        {"account_id": f"eq.{ACCOUNT}", "milestone": "eq.M1"},
    )
    halted = await svc.cancel_account(ACCOUNT)
    assert halted == 2  # only M2/M3 still pending
    statuses = {r["milestone"]: r["status"] for r in svc.db.rows}
    assert statuses["M1"] == "paid"


async def test_cancel_other_account_untouched(svc):
    await _schedule(svc)
    await _schedule(svc, account_id="org-9999")
    await svc.cancel_account(ACCOUNT)
    other = [r for r in svc.db.rows if r["account_id"] == "org-9999"]
    assert {r["status"] for r in other} == {"earned", "pending"}


async def test_rep_summary(svc):
    await _schedule(svc)
    summary = await svc.rep_summary(REP)
    assert summary["earned_unpaid_cents"] == 9750       # M0 earned, not yet paid
    assert summary["pending_cents"] == 33000            # M1+M2+M3 scheduled
    assert summary["paid_cents"] == 0
    assert summary["next_payday"] == "2026-07-31"
    assert summary["next_payday_amount_cents"] == 9750
    assert summary["currency"] == "CAD"
