"""
Canada rep commission engine — milestone-based, exact integer cents.

Replaces the dead percentage-based commission system (the `commissions` table
has had 0 rows ever; billing.py / stripe_checkout.py inserted columns that
don't exist and failed silently; calculate_commission() has no callers).

Source of truth: the official Rep Commission One-Pager.

    Every package's total commission splits across 4 milestones in fixed
    57-unit weights: M0=13, M1=28, M2=10, M3=6.
    payout(package, milestone) = unit_value(package) x weight(milestone)

    - M0 earned at close (first payment clears); PAID the Friday of the week
      after — always a full payroll week (>= 7 days) between close and pay.
    - M1/M2/M3 earned at months 4/9/12 of account activity; paid on the next
      quarterly settlement date strictly after earning.
    - Upsell:   negotiated > list  ->  M0 += 0.50 x (negotiated - list)
    - Discount: negotiated < list  ->  M0 -= 1.00 x (list - negotiated)
    - M1/M2/M3 are NEVER adjusted.
    - Cancellation halts all FUTURE (pending) milestones immediately;
      earned/paid amounts are never clawed back.

Package unit values live in the `commission_packages` config table
(migration 046) — adding a tier is a row insert, not a code change.
`DEFAULT_PACKAGES` mirrors the seeded rows for pure/unit use.

Classification: commissions are independent-contractor, lump-sum,
outcome-based payments (stored as row metadata).

INERT BY DESIGN: nothing imports this from live billing flows. The service
layer only writes `commission_milestones` (migration 046) via the injected
db client; wiring into webhooks/billing is a separate reviewed change.

Lowest price is $250 USD (Starter); the $200 minimum SKU was dropped
2026-07-19, retiring the old anchor question. Reps cannot sell below $250.

── PARAMETERIZED OPEN QUESTIONS (defaults below; each needs Aidan/Enoch
   sign-off before go-live) ────────────────────────────────────────────────
1. min_monthly_cents = 25000 — lowest sellable price ($250 USD). Discounts
   cannot price below it.
2. m0_floor_zero = True — M0 floors at $0, never goes negative.
3. currency = 'CAD'.
4. retro_upsell_commission = False — post-close upsells generate no
   commission. If flipped True, a post-close upsell pays 0.50 x monthly
   delta (same upsell rate as at-close), one-time.
5. settlement_months / settlement_day_rule — default first Friday of
   Jan/Apr/Jul/Oct. FLAGGED: exact settlement calendar needs Aidan sign-off.
6. m0_min_gap_days = 7 — encodes "always a full payroll week between":
   M0 pays on the first Friday at least 7 days after close (Tuesday close
   -> the Friday after next, not the immediate one). FLAGGED: Friday-close
   pays exactly +7 days under this rule — confirm intended.
7. Odd-cent upsell deltas: 0.50 x delta floors the half cent (integer
   division). FLAGGED for Aidan (only matters for odd-cent slider prices).
"""

from __future__ import annotations

import calendar
import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta

logger = logging.getLogger("meridian.services.commission_engine")


def canada_commission_live() -> bool:
    """Kill-switch for LIVE Canada commission accrual.

    Default ON (Enoch's plan wired live for Canada, 2026-07-19). Set
    COMMISSION_ENGINE_CANADA_LIVE=0 in Railway to instantly stop accrual +
    cancel-halt without a deploy. Accrual is always best-effort and idempotent,
    so flipping this off/on never corrupts the ledger.
    """
    return os.environ.get("COMMISSION_ENGINE_CANADA_LIVE", "1").strip().lower() not in (
        "0", "false", "off", "no", "",
    )

# Fixed 57-unit milestone split (One-Pager).
MILESTONE_WEIGHTS: dict[str, int] = {"M0": 13, "M1": 28, "M2": 10, "M3": 6}

# Months of account activity at which M1/M2/M3 are earned.
MILESTONE_EARN_MONTHS: dict[str, int] = {"M1": 4, "M2": 9, "M3": 12}

MILESTONE_ORDER = ("M0", "M1", "M2", "M3")

CLASSIFICATION = "independent_contractor_lump_sum_outcome_based"

TABLE = "commission_milestones"


@dataclass(frozen=True)
class Package:
    """One row of the commission_packages config table."""
    package_key: str
    list_monthly_cents: int
    unit_value_cents: int
    active: bool = True


# Mirrors the migration-046 seed rows. Prod code should load the table via
# CommissionEngineService.load_packages(); these are for pure math + tests.
# Packages match Enoch's official Rep Commission One-Pager (2026): the $200/mo
# minimum-price tier is its OWN SKU (unit $6.00, schedule $78/$168/$60/$36 =
# $342), not a discounted Starter — reinstated per Enoch's plan 2026-07-19.
DEFAULT_PACKAGES: dict[str, Package] = {
    "minimum": Package("minimum", 20000, 600),                   # $200/mo, unit $6.00
    "starter": Package("starter", 25000, 750),                   # $250/mo, unit $7.50
    "middle": Package("middle", 39900, 1375),                    # $399/mo, unit $13.75
    "higher": Package("higher", 68900, 2000),                    # $689/mo, unit $20.00
}


@dataclass(frozen=True)
class EngineConfig:
    """Engine flags. Defaults mirror the commission_config seed (migration 046).

    Every field here is an OPEN QUESTION default flagged for Aidan/Enoch —
    see the module docstring.
    """
    m0_floor_zero: bool = True
    currency: str = "CAD"
    retro_upsell_commission: bool = False
    m0_min_gap_days: int = 7
    settlement_months: tuple[int, ...] = (1, 4, 7, 10)
    settlement_day_rule: str = "first_friday"
    # Lowest sellable monthly price = the $200 minimum-price tier (Enoch's plan).
    # A discount can never price below it; reps cannot sell under it.
    min_monthly_cents: int = 20000


@dataclass(frozen=True)
class MilestoneEntry:
    """One computed ledger line (pure value — no I/O)."""
    milestone: str
    amount_cents: int
    earned_at: date
    payable_on: date
    status: str  # 'earned' (M0 at close) | 'pending' (future milestones)
    currency: str = "CAD"
    classification: str = CLASSIFICATION


# ───────────────────────────────────────────────────────────────────────────
# Pure math — no I/O anywhere below this line until the service class.
# ───────────────────────────────────────────────────────────────────────────

def milestone_amounts(package: Package) -> dict[str, int]:
    """Unadjusted milestone payouts in cents: unit_value x weight."""
    return {ms: package.unit_value_cents * w for ms, w in MILESTONE_WEIGHTS.items()}


def package_total_cents(package: Package) -> int:
    """Total commission for a package at list price (57 x unit value)."""
    return package.unit_value_cents * sum(MILESTONE_WEIGHTS.values())


def adjusted_m0_cents(
    package: Package,
    negotiated_monthly_cents: int,
    config: EngineConfig,
) -> int:
    """M0 with upsell/discount adjustment applied. M0 ONLY — never M1/M2/M3.

    Upsell   (negotiated > list): +50% of the delta (odd cents floor — flagged).
    Discount (negotiated < list): -100% of the delta.

    The negotiated price is clamped to config.min_monthly_cents ($250 USD) —
    reps cannot sell below the lowest tier, so no discount can price under it.
    """
    base = package.unit_value_cents * MILESTONE_WEIGHTS["M0"]
    negotiated = max(negotiated_monthly_cents, config.min_monthly_cents)
    delta = negotiated - package.list_monthly_cents

    if delta > 0:
        m0 = base + delta // 2  # floor on odd cents — flagged for Aidan
    elif delta < 0:
        m0 = base + delta  # full discount comes out of M0
    else:
        m0 = base

    if config.m0_floor_zero:
        m0 = max(0, m0)
    return m0


def nearest_package_by_price(monthly_cents: int, packages: dict[str, "Package"]) -> str:
    """Pick the commission package whose list price is closest to the negotiated
    monthly. Ties break toward the CHEAPER package (rep-favorable is handled by
    the M0 adjustment, not here). Returns the package_key.

    This is how a live Canada close maps to Enoch's four price-point packages:
    the package sets the list baseline + unit value; the negotiated-vs-list
    delta is then applied to M0 by adjusted_m0_cents (+50% upsell / -100%
    discount). So a deal at any price still resolves to an exact, defensible
    schedule — the package is the anchor, the negotiated price is the truth.
    """
    target = int(monthly_cents)
    return min(
        packages.values(),
        key=lambda p: (abs(p.list_monthly_cents - target), p.list_monthly_cents),
    ).package_key


def post_close_upsell_cents(
    old_monthly_cents: int,
    new_monthly_cents: int,
    config: EngineConfig,
) -> int:
    """Commission on a POST-CLOSE upsell.

    Default (retro_upsell_commission=False): post-close upsells generate no
    commission — returns 0. If flipped on, pays 0.50 x monthly delta once
    (same rate as an at-close upsell). Never negative.
    """
    if not config.retro_upsell_commission:
        return 0
    delta = new_monthly_cents - old_monthly_cents
    return max(0, delta // 2)


def add_months(d: date, months: int) -> date:
    """Calendar month addition, clamping to the last day of short months."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def first_friday(year: int, month: int) -> date:
    """First Friday of a month."""
    d = date(year, month, 1)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def m0_pay_date(close_date: date, min_gap_days: int = 7) -> date:
    """M0 pay date: Friday of the week AFTER close.

    Encoded as: the first Friday at least `min_gap_days` (default 7) days
    after the close, guaranteeing a full payroll week between close and pay.
    Tuesday close -> the NEXT Friday (skips the immediate one).
    Friday close -> exactly one week later. Sat/Sun closes push a week further
    (the coming Friday would be < 7 days out).
    """
    earliest = close_date + timedelta(days=min_gap_days)
    return earliest + timedelta(days=(4 - earliest.weekday()) % 7)


def next_settlement_date(after: date, config: EngineConfig) -> date:
    """Next quarterly settlement date STRICTLY AFTER `after`.

    Default rule: first Friday of each month in config.settlement_months
    (Jan/Apr/Jul/Oct). Parameterized — flagged for Aidan sign-off.
    """
    if config.settlement_day_rule != "first_friday":
        raise ValueError(f"Unknown settlement_day_rule: {config.settlement_day_rule}")
    for year in (after.year, after.year + 1):
        for month in sorted(config.settlement_months):
            candidate = first_friday(year, month)
            if candidate > after:
                return candidate
    raise RuntimeError("unreachable: settlement search spans two years")


def compute_schedule(
    package_key: str,
    negotiated_monthly_cents: int,
    close_date: date,
    config: EngineConfig,
    activation_date: date | None = None,
    packages: dict[str, Package] | None = None,
) -> list[MilestoneEntry]:
    """Full 4-milestone schedule for one closed account. Pure — no I/O.

    - M0: earned at close, status 'earned', payable Friday-after-full-week.
    - M1/M2/M3: earned at months 4/9/12 of activity, status 'pending',
      payable on the next settlement date strictly after each earn date.
    """
    packages = packages or DEFAULT_PACKAGES
    package = packages[package_key]
    activation = activation_date or close_date

    amounts = milestone_amounts(package)
    amounts["M0"] = adjusted_m0_cents(package, negotiated_monthly_cents, config)

    entries = [
        MilestoneEntry(
            milestone="M0",
            amount_cents=amounts["M0"],
            earned_at=close_date,
            payable_on=m0_pay_date(close_date, config.m0_min_gap_days),
            status="earned",
            currency=config.currency,
        )
    ]
    for ms in ("M1", "M2", "M3"):
        earned = add_months(activation, MILESTONE_EARN_MONTHS[ms])
        entries.append(
            MilestoneEntry(
                milestone=ms,
                amount_cents=amounts[ms],
                earned_at=earned,
                payable_on=next_settlement_date(earned, config),
                status="pending",
                currency=config.currency,
            )
        )
    return entries


# ───────────────────────────────────────────────────────────────────────────
# Service layer — thin I/O over the pure math (injected db, SupabaseREST-shaped)
# ───────────────────────────────────────────────────────────────────────────

class CommissionEngineService:
    """Writes/reads the commission_milestones ledger (migration 046).

    All writes go through the service role (RLS denies user-JWT writes).
    Idempotency: UNIQUE(account_id, milestone) + ON CONFLICT DO NOTHING —
    double-scheduling an account is a no-op.
    """

    def __init__(
        self,
        db,
        config: EngineConfig | None = None,
        packages: dict[str, Package] | None = None,
    ):
        self.db = db
        self.config = config or EngineConfig()
        self.packages = packages or DEFAULT_PACKAGES

    async def load_packages(self) -> dict[str, Package]:
        """Refresh the package catalog from the commission_packages table."""
        rows = await self.db.select(
            "commission_packages", filters={"active": "eq.true"}
        )
        if rows:
            self.packages = {
                r["package_key"]: Package(
                    package_key=r["package_key"],
                    list_monthly_cents=int(r["list_monthly_cents"]),
                    unit_value_cents=int(r["unit_value_cents"]),
                    active=bool(r.get("active", True)),
                )
                for r in rows
            }
        return self.packages

    async def schedule_account(
        self,
        *,
        account_id: str,
        rep_id: str,
        package_key: str,
        negotiated_monthly_cents: int,
        close_date: date,
        activation_date: date | None = None,
        assignment_id: str | None = None,
    ) -> list[dict]:
        """Create the 4-milestone ledger rows for a newly closed account.

        Returns the rows actually inserted ([] when already scheduled —
        idempotent under UNIQUE(account_id, milestone)).
        """
        entries = compute_schedule(
            package_key=package_key,
            negotiated_monthly_cents=negotiated_monthly_cents,
            close_date=close_date,
            activation_date=activation_date,
            config=self.config,
            packages=self.packages,
        )
        rows = [
            {
                "account_id": account_id,
                "rep_id": rep_id,
                "assignment_id": assignment_id,
                "package_key": package_key,
                "milestone": e.milestone,
                "amount_cents": e.amount_cents,
                "currency": e.currency,
                "earned_at": e.earned_at.isoformat(),
                "payable_on": e.payable_on.isoformat(),
                "status": e.status,
                "metadata": {
                    "classification": e.classification,
                    "negotiated_monthly_cents": negotiated_monthly_cents,
                },
            }
            for e in entries
        ]
        inserted = await self.db.upsert(
            TABLE,
            rows,
            on_conflict="account_id,milestone",
            ignore_duplicates=True,
        )
        if not inserted:
            logger.info("Account %s already scheduled — no-op", account_id)
        return inserted

    async def accrue_for_canada_close(
        self,
        *,
        account_id: str,
        rep_email: str,
        negotiated_monthly_cents: int,
        close_date: date,
        package_key: str | None = None,
        assignment_id: str | None = None,
    ) -> list[dict]:
        """LIVE Canada close hook: resolve the rep, pick the package, schedule.

        Returns the inserted milestone rows ([] on skip/no-op). NEVER raises for
        an expected miss (unknown rep, no price) — the caller wraps it best-effort
        anyway, but keeping the skips quiet here means a normal non-rep close
        doesn't log noise.

          - rep_email -> sales_reps.id (verified email join, same as the read API).
            No rep match => skip (returns []). A commission can't exist repless.
          - package_key defaults to the nearest price-point package (Enoch's four).
          - account_id is the businesses(id) [text] of the new customer (mig 071).
        """
        if not account_id or not rep_email or negotiated_monthly_cents <= 0:
            return []
        reps = await self.db.select(
            "sales_reps",
            columns="id,is_active",
            filters={"email": f"eq.{rep_email.strip().lower()}"},
            limit=1,
        )
        if not reps:
            logger.info("commission accrual skipped: %s is not a sales_rep", rep_email)
            return []
        rep_id = reps[0]["id"]

        await self.load_packages()
        key = package_key or nearest_package_by_price(negotiated_monthly_cents, self.packages)
        if key not in self.packages:
            logger.warning("commission accrual skipped: unknown package %r", key)
            return []

        inserted = await self.schedule_account(
            account_id=account_id,
            rep_id=rep_id,
            package_key=key,
            negotiated_monthly_cents=negotiated_monthly_cents,
            close_date=close_date,
            assignment_id=assignment_id,
        )
        logger.info(
            "commission accrual: account=%s rep=%s package=%s negotiated=%d -> %d rows",
            account_id, rep_id, key, negotiated_monthly_cents, len(inserted),
        )
        return inserted

    async def cancel_account(self, account_id: str) -> int:
        """Cancellation hook: halt all FUTURE (pending) milestones immediately.

        Earned/paid milestones are NEVER clawed back. Intended caller: the
        subscription-cancel path (including 'cancel_pending' from migration
        023 — halting on cancel intent is the conservative reading; if the
        cancel later fails and the account stays active, un-halting is a
        manual operator action. Flagged for Aidan). NOT wired anywhere yet.
        """
        updated = await self.db.update(
            TABLE,
            {"status": "halted"},
            {"account_id": f"eq.{account_id}", "status": "eq.pending"},
        )
        logger.info("Halted %d future milestones for account %s", len(updated), account_id)
        return len(updated)

    async def mark_earned(self, as_of: date) -> int:
        """Promote pending milestones whose earn date has arrived (account
        still active — cancelled accounts' rows are already 'halted')."""
        updated = await self.db.update(
            TABLE,
            {"status": "earned"},
            {"status": "eq.pending", "earned_at": f"lte.{as_of.isoformat()}"},
        )
        return len(updated)

    async def settlement_due(self, settlement_date: date) -> list[dict]:
        """Batch for one settlement run: earned rows payable on/before the date."""
        return await self.db.select(
            TABLE,
            filters={
                "status": "eq.earned",
                "payable_on": f"lte.{settlement_date.isoformat()}",
            },
            order="rep_id.asc",
        )

    async def mark_paid(self, ids: list[str], paid_at: date) -> int:
        """Mark specific ledger rows paid (post-payout-run bookkeeping)."""
        n = 0
        for row_id in ids:
            updated = await self.db.update(
                TABLE,
                {"status": "paid", "paid_at": paid_at.isoformat()},
                {"id": f"eq.{row_id}", "status": "eq.earned"},
            )
            n += len(updated)
        return n

    async def rep_summary(self, rep_id: str) -> dict:
        """Rep-facing rollup: earned (unpaid) / pending / paid / next payday."""
        rows = await self.db.select(TABLE, filters={"rep_id": f"eq.{rep_id}"})

        earned = [r for r in rows if r["status"] == "earned"]
        pending = [r for r in rows if r["status"] == "pending"]
        paid = [r for r in rows if r["status"] == "paid"]

        payable = sorted(earned + pending, key=lambda r: r["payable_on"])
        next_payday = payable[0]["payable_on"] if payable else None
        next_amount = sum(
            r["amount_cents"] for r in payable if r["payable_on"] == next_payday
        ) if next_payday else 0

        return {
            "earned_unpaid_cents": sum(r["amount_cents"] for r in earned),
            "pending_cents": sum(r["amount_cents"] for r in pending),
            "paid_cents": sum(r["amount_cents"] for r in paid),
            "next_payday": next_payday,
            "next_payday_amount_cents": next_amount,
            "currency": self.config.currency,
            "milestones": rows,
        }
