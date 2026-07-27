"""US rep commission — DECLINING REVENUE-SHARE model.

This is a DIFFERENT model from the milestone engine in commission_engine.py
(fixed M0-M3 lump sums per package, used by Canada). US reps earn a PERCENTAGE
of the revenue their account brings in each period, halving every year:

    Year 1  (months  1-12):  45.00%
    Year 2  (months 13-24):  22.50%   (halved)
    Year 3  (months 25-36):  11.25%   (halved again)
    Year 4+ (month 37+):      0%       (no further commission)

"Every dollar brought in" = the recurring revenue Meridian collects from the
account in that month (the calculator is basis-agnostic — pass whatever counts:
the contracted monthly fee alone, or monthly fee + order fees). Commission is
TRAILING: it accrues per active/paid month, so a rep is paid as the account
pays — nothing is over-promised if the merchant churns early.

The functions here are PURE (no I/O) so the money math is exhaustively unit-
tested and can be previewed for any deal size BEFORE a rep ever sells (see
scripts/us_commission_preview.py). Wiring accrual to real billing cycles is a
separate, mechanical step gated behind a default-OFF flag.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

# ── The schedule (single source of truth) ────────────────────────────────────
YEAR1_RATE = 0.45
ANNUAL_DECAY = 0.5           # rate halves each subsequent year
COMMISSIONED_YEARS = 3       # years 1-3 pay; year 4+ pays nothing
MONTHS_PER_YEAR = 12
COMMISSIONED_MONTHS = COMMISSIONED_YEARS * MONTHS_PER_YEAR  # 36


def us_commission_live() -> bool:
    """Kill-switch for LIVE US revenue-share accrual. Default OFF — the model is
    proven by tests + preview, but real accrual stays inert until the business
    turns it on (COMMISSION_US_REVSHARE_LIVE=1). Independent of the milestone
    engine's COMMISSION_ENGINE_US_LIVE (that flag pays the WRONG, Canada model)."""
    return os.environ.get("COMMISSION_US_REVSHARE_LIVE", "0").strip().lower() in (
        "1", "true", "on", "yes",
    )


def commission_year_for_month(month_index: int) -> int:
    """Account-year (1-based) for the Nth month after close. month_index=1 is the
    first month; months 1-12 → year 1, 13-24 → year 2, etc."""
    if month_index < 1:
        return 0
    return (month_index - 1) // MONTHS_PER_YEAR + 1


def us_commission_rate(month_index: int) -> float:
    """Commission rate for the Nth month after close. 45% in year 1, halving each
    year, 0 once past the commissioned window (month 37+)."""
    year = commission_year_for_month(month_index)
    if year < 1 or year > COMMISSIONED_YEARS:
        return 0.0
    return round(YEAR1_RATE * (ANNUAL_DECAY ** (year - 1)), 6)


def commission_cents_for_month(revenue_cents: int, month_index: int) -> int:
    """Commission owed for ONE month, given that month's collected revenue.
    Rounded to whole cents (round-half-to-even, Python default)."""
    if not revenue_cents or revenue_cents <= 0:
        return 0
    return int(round(revenue_cents * us_commission_rate(month_index)))


def months_since_close(close: date, as_of: date) -> int:
    """1-based month index of `as_of` relative to `close`. The close month is
    month 1; each whole calendar-month boundary advances it. Never negative."""
    if as_of < close:
        return 0
    return (as_of.year - close.year) * 12 + (as_of.month - close.month) + 1


@dataclass(frozen=True)
class MonthRow:
    month: int
    year: int
    rate: float
    revenue_cents: int
    commission_cents: int
    cumulative_cents: int


def project_commission(monthly_revenue_cents: int,
                       months: int = COMMISSIONED_MONTHS) -> list[MonthRow]:
    """Month-by-month projection for a steady monthly revenue — the pre-sale
    preview. Assumes the account stays active + pays the same amount each month;
    real accrual uses the ACTUAL collected amount per period."""
    rows: list[MonthRow] = []
    cumulative = 0
    for m in range(1, months + 1):
        c = commission_cents_for_month(monthly_revenue_cents, m)
        cumulative += c
        rows.append(MonthRow(
            month=m,
            year=commission_year_for_month(m),
            rate=us_commission_rate(m),
            revenue_cents=monthly_revenue_cents,
            commission_cents=c,
            cumulative_cents=cumulative,
        ))
    return rows


def year_totals_cents(monthly_revenue_cents: int) -> dict[int, int]:
    """Total commission per account-year for a steady monthly revenue
    ({1: yr1, 2: yr2, 3: yr3})."""
    totals: dict[int, int] = {}
    for r in project_commission(monthly_revenue_cents):
        totals[r.year] = totals.get(r.year, 0) + r.commission_cents
    return totals


def lifetime_commission_cents(monthly_revenue_cents: int) -> int:
    """Total commission a rep earns over the full 3-year commissioned window for
    a steady monthly revenue."""
    rows = project_commission(monthly_revenue_cents)
    return rows[-1].cumulative_cents if rows else 0
