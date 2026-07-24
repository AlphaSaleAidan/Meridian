"""US declining revenue-share commission — exhaustive money-math proof.

Every boundary and every rate is pinned to a hand-computed value so the model is
provably correct before a rep ever sells. If any number here changes, the comp
plan changed — that must be deliberate.

    Year 1 (m 1-12):  45.00%
    Year 2 (m 13-24): 22.50%
    Year 3 (m 25-36): 11.25%
    Year 4+ (m 37+):  0%
"""
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services import us_commission as uc  # noqa: E402


# ── rate schedule + year boundaries ──────────────────────────────────────────

@pytest.mark.parametrize("month,year,rate", [
    (0, 0, 0.0), (-3, 0, 0.0),
    (1, 1, 0.45), (12, 1, 0.45),
    (13, 2, 0.225), (24, 2, 0.225),
    (25, 3, 0.1125), (36, 3, 0.1125),
    (37, 4, 0.0), (48, 4, 0.0), (120, 10, 0.0),
])
def test_rate_and_year_at_every_boundary(month, year, rate):
    assert uc.commission_year_for_month(month) == year
    assert uc.us_commission_rate(month) == rate


def test_each_year_is_half_the_previous():
    assert uc.us_commission_rate(13) == uc.us_commission_rate(1) / 2
    assert uc.us_commission_rate(25) == uc.us_commission_rate(13) / 2
    assert uc.us_commission_rate(37) == 0.0


# ── per-month commission (exact cents) ───────────────────────────────────────

def test_month_commission_350_per_month():
    r = 35000  # $350/mo
    assert uc.commission_cents_for_month(r, 1) == 15750   # 45%
    assert uc.commission_cents_for_month(r, 13) == 7875   # 22.5%
    assert uc.commission_cents_for_month(r, 25) == 3938   # 11.25% (3937.5 → 3938)
    assert uc.commission_cents_for_month(r, 37) == 0      # year 4


def test_zero_or_negative_revenue_is_zero():
    assert uc.commission_cents_for_month(0, 1) == 0
    assert uc.commission_cents_for_month(-100, 1) == 0


# ── full projections (exact cents), the numbers a rep is quoted ──────────────

@pytest.mark.parametrize("monthly,yr1,yr2,yr3,lifetime", [
    (25000, 135000, 67500, 33744, 236244),   # $250/mo  → $2,362.44 over 3 yrs
    (35000, 189000, 94500, 47256, 330756),   # $350/mo  → $3,307.56
    (50000, 270000, 135000, 67500, 472500),  # $500/mo  → $4,725.00
])
def test_year_totals_and_lifetime(monthly, yr1, yr2, yr3, lifetime):
    totals = uc.year_totals_cents(monthly)
    assert totals == {1: yr1, 2: yr2, 3: yr3}
    assert uc.lifetime_commission_cents(monthly) == lifetime
    # sanity: lifetime is the sum of the three years, and year 4 pays nothing
    assert lifetime == yr1 + yr2 + yr3
    assert 4 not in totals


def test_projection_has_36_commissioned_months():
    rows = uc.project_commission(35000)
    assert len(rows) == 36
    assert rows[-1].cumulative_cents == uc.lifetime_commission_cents(35000)
    # cumulative is monotonic and never decreases
    assert all(rows[i].cumulative_cents >= rows[i - 1].cumulative_cents
               for i in range(1, len(rows)))


# ── month index from real dates (drives real accrual) ────────────────────────

def test_months_since_close():
    close = date(2026, 7, 25)
    assert uc.months_since_close(close, date(2026, 7, 25)) == 1    # close month = m1
    assert uc.months_since_close(close, date(2026, 8, 1)) == 2
    assert uc.months_since_close(close, date(2027, 7, 10)) == 13   # start of year 2
    assert uc.months_since_close(close, date(2028, 7, 1)) == 25    # start of year 3
    assert uc.months_since_close(close, date(2029, 7, 1)) == 37    # year 4 → 0% rate
    assert uc.months_since_close(close, date(2026, 6, 1)) == 0     # before close


def test_live_gate_defaults_off_and_is_independent(monkeypatch):
    monkeypatch.delenv("COMMISSION_US_REVSHARE_LIVE", raising=False)
    assert uc.us_commission_live() is False
    monkeypatch.setenv("COMMISSION_US_REVSHARE_LIVE", "1")
    assert uc.us_commission_live() is True
