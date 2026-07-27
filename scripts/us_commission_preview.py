#!/usr/bin/env python3
"""Pre-sale preview of the US declining revenue-share commission.

Prints the exact rep payout for any monthly deal size so the plan can be
sanity-checked BEFORE anyone sells. Pure math (same functions the engine uses) —
no DB, no side effects.

    python3 scripts/us_commission_preview.py                 # default deal sizes
    python3 scripts/us_commission_preview.py 350 500 750     # $/mo values
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services import us_commission as uc  # noqa: E402


def _d(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def preview(monthly_dollars: float) -> None:
    monthly_cents = int(round(monthly_dollars * 100))
    totals = uc.year_totals_cents(monthly_cents)
    lifetime = uc.lifetime_commission_cents(monthly_cents)

    print(f"\n  DEAL: {_d(monthly_cents)}/mo   ({_d(monthly_cents * 12)}/yr revenue)")
    print("  " + "-" * 58)
    print(f"  {'Year':<6}{'Rate':>8}{'Rep / month':>16}{'Rep / year':>18}")
    print("  " + "-" * 58)
    for yr in (1, 2, 3):
        month_index = (yr - 1) * 12 + 1
        rate = uc.us_commission_rate(month_index)
        per_month = uc.commission_cents_for_month(monthly_cents, month_index)
        print(f"  {yr:<6}{rate * 100:>6.2f}%{_d(per_month):>16}{_d(totals[yr]):>18}")
    print(f"  {'4+':<6}{'0.00%':>8}{_d(0):>16}{_d(0):>18}")
    print("  " + "-" * 58)
    print(f"  {'3-YEAR TOTAL TO REP':<30}{_d(lifetime):>28}")


def main(argv: list[str]) -> int:
    deals = [float(a) for a in argv[1:]] if len(argv) > 1 else [250, 350, 500]
    print("\n== US REP COMMISSION — declining revenue-share ==")
    print("   Yr1 45%  ·  Yr2 22.5%  ·  Yr3 11.25%  ·  Yr4+ 0%")
    print("   Basis: recurring revenue collected from the account each month.")
    for d in deals:
        preview(d)
    print("\n   (Trailing: accrues only for months the account actually pays.)")
    print(f"   LIVE accrual gate COMMISSION_US_REVSHARE_LIVE = "
          f"{'ON' if uc.us_commission_live() else 'OFF (default)'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
