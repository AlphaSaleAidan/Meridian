"""
Canonical deal fee terms + merchant_billing_terms access.

SINGLE BACKEND SOURCE OF TRUTH for the 3-tier pricing fee schedule.

The frontend plan files MUST stay in sync with CANONICAL_FEE_TERMS below:
  frontend/src/lib/proposal-plans.ts         (US tiers)
  frontend/src/lib/canada-proposal-plans.ts  (CA tiers)
`canonical_fee_terms_json()` exports the same table as JSON so those files can
eventually be generated from (or validated against) this module instead of
hand-mirrored.

Terminology (all money in integer cents of the market currency):
  plan_tier                   standard | premium | command
  monthly_fee_cents           monthly subscription price
  order_fee_cents             flat Meridian fee per phone/website order
  call_overage_cents_per_min  per-minute charge past the included call block
  included_call_min           minutes included per AI call before overage

merchant_billing_terms doctrine: supersede-not-update. `set_merchant_billing_
terms` closes the active row (superseded_at=now) and inserts a fresh one; the
row history is the audit trail. Exactly one active row per merchant (partial
unique index, migration 20260716_merchant_billing_terms.sql).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("meridian.billing.fee_terms")

MARKETS = ("us", "ca")
PLAN_TIER_IDS = ("standard", "premium", "command")

# Env-default call terms (mirrors vapi_webhook VOICE_INCLUDED_MIN /
# VOICE_OVERAGE_CENTS_PER_MIN defaults). Both markets currently bill the same
# nominal overage figure in their local currency.
DEFAULT_INCLUDED_CALL_MIN = 3
DEFAULT_CALL_OVERAGE_CENTS_PER_MIN = 45

# Fee terms fields shared by canada_leads/us_leads and merchant_billing_terms.
FEE_TERM_FIELDS = (
    "plan_tier",
    "monthly_fee_cents",
    "order_fee_cents",
    "call_overage_cents_per_min",
    "included_call_min",
)

# ── Per-order fee floors + cap (rep-slider redlines) ─────────────────────────
# SINGLE SOURCE OF TRUTH for the slider redlines and the hard per-order cap.
# USD constants are canonical; CAD values are DERIVED via the standard CAD
# multiplier ×1.4, then ROUNDED DOWN to the nearest 5¢ for clean pricing
# (Aidan 2026-07-19 — supersedes the hand-set CA$0.85/CA$0.65 of 2026-07-15):
# premium 65¢→90¢→CA$0.90, command 45¢→60¢→CA$0.60, cap $5.00→CA$7.00.
# Rounding DOWN keeps the CAD floor at/below the raw multiple, so it never
# quotes above the intended redline. A US floor change propagates automatically.
CAD_FEE_MULTIPLIER = 1.4
CAD_ROUND_DOWN_TO_CENTS = 5


def cad_fee_cents(usd_cents: int) -> int:
    """USD cents → CAD cents via ×1.4, rounded DOWN to the nearest 5¢."""
    raw = usd_cents * CAD_FEE_MULTIPLIER
    return int(raw // CAD_ROUND_DOWN_TO_CENTS) * CAD_ROUND_DOWN_TO_CENTS


ORDER_FEE_FLOOR_CENTS_USD: dict[str, int] = {"standard": 0, "premium": 65, "command": 45}
ORDER_FEE_CAP_CENTS_USD = 500

# CAD overrides that deliberately BREAK the ×1.4 derivation (Aidan 2026-08-07).
# CA premium is CA$0.75 ALL-IN: that is the merchant's total per-order cost
# including Stripe's flat 30¢, which Meridian now absorbs instead of passing
# through (STRIPE_FEE_FIXED_CENTS=0) — so Meridian nets CA$0.45. Derivation
# would say 90¢; the cut is a deliberate CA-only price move, not a rounding.
ORDER_FEE_FLOOR_CENTS_CAD_OVERRIDE: dict[str, int] = {"premium": 75}

# Market-keyed views ('us' | 'ca') — the only floor/cap tables consumers read.
ORDER_FEE_FLOOR_CENTS: dict[str, dict[str, int]] = {
    "us": ORDER_FEE_FLOOR_CENTS_USD,
    "ca": {tier: ORDER_FEE_FLOOR_CENTS_CAD_OVERRIDE.get(tier, cad_fee_cents(v))
           for tier, v in ORDER_FEE_FLOOR_CENTS_USD.items()},
}
ORDER_FEE_CAP_CENTS: dict[str, int] = {
    "us": ORDER_FEE_CAP_CENTS_USD,
    "ca": cad_fee_cents(ORDER_FEE_CAP_CENTS_USD),
}

# ── Canonical tier table ─────────────────────────────────────────────────────
# Values mirror the frontend plan files (see module docstring):
#   US: Standard $250 / Premium $350 ($0.65/order) / Command $500 ($0.45/order)
#   CA: Standard CA$350 / Premium CA$500 (CA$0.90/order)
#       / Command CA$700 (CA$0.60/order)
# 2026-08-06 (Aidan): per-order fees adjusted DOWN to the former redlines and
# FIXED — the rep fee slider is retired, so order_fee_cents == the floor.
# canada.py still clamps client-sent fees to ORDER_FEE_FLOOR_CENTS.
CANONICAL_FEE_TERMS: dict[str, dict[str, dict[str, int]]] = {
    "us": {
        "standard": {
            "monthly_fee_cents": 25000,
            "order_fee_cents": 0,
            "order_fee_floor_cents": ORDER_FEE_FLOOR_CENTS["us"]["standard"],
            "call_overage_cents_per_min": DEFAULT_CALL_OVERAGE_CENTS_PER_MIN,
            "included_call_min": DEFAULT_INCLUDED_CALL_MIN,
        },
        "premium": {
            "monthly_fee_cents": 35000,
            "order_fee_cents": 65,
            "order_fee_floor_cents": ORDER_FEE_FLOOR_CENTS["us"]["premium"],
            "call_overage_cents_per_min": DEFAULT_CALL_OVERAGE_CENTS_PER_MIN,
            "included_call_min": DEFAULT_INCLUDED_CALL_MIN,
        },
        "command": {
            "monthly_fee_cents": 50000,
            "order_fee_cents": 45,
            "order_fee_floor_cents": ORDER_FEE_FLOOR_CENTS["us"]["command"],
            "call_overage_cents_per_min": DEFAULT_CALL_OVERAGE_CENTS_PER_MIN,
            "included_call_min": DEFAULT_INCLUDED_CALL_MIN,
        },
    },
    "ca": {
        "standard": {
            "monthly_fee_cents": 35000,
            "order_fee_cents": 0,
            "order_fee_floor_cents": ORDER_FEE_FLOOR_CENTS["ca"]["standard"],
            "call_overage_cents_per_min": DEFAULT_CALL_OVERAGE_CENTS_PER_MIN,
            "included_call_min": DEFAULT_INCLUDED_CALL_MIN,
        },
        "premium": {
            "monthly_fee_cents": 50000,
            "order_fee_cents": 75,
            "order_fee_floor_cents": ORDER_FEE_FLOOR_CENTS["ca"]["premium"],
            "call_overage_cents_per_min": DEFAULT_CALL_OVERAGE_CENTS_PER_MIN,
            "included_call_min": DEFAULT_INCLUDED_CALL_MIN,
        },
        "command": {
            "monthly_fee_cents": 70000,
            "order_fee_cents": 60,
            "order_fee_floor_cents": ORDER_FEE_FLOOR_CENTS["ca"]["command"],
            "call_overage_cents_per_min": DEFAULT_CALL_OVERAGE_CENTS_PER_MIN,
            "included_call_min": DEFAULT_INCLUDED_CALL_MIN,
        },
    },
}

# Rep price-slider headroom on top of a tier's base monthly (proposal-plans
# REP_PRICE_HEADROOM / REP_PRICE_HEADROOM_CAD). Used only for sanity clamping.
REP_PRICE_HEADROOM_CENTS = {"us": 10000, "ca": 15000}

DEFAULT_PLAN_TIER = "premium"  # matches the frontend getPlan() fallback

LEAD_TABLE_BY_MARKET = {"ca": "canada_leads", "us": "us_leads"}


def canonical_fee_terms_json() -> str:
    """The canonical tier table as stable JSON (for export / frontend adoption)."""
    return json.dumps(CANONICAL_FEE_TERMS, sort_keys=True, indent=2)


def normalize_market(value: Optional[str]) -> str:
    """'CA'/'canada'/'cad' → 'ca'; 'US'/'usa'/'usd' → 'us'. Default 'ca'
    (matches provision_customer's country default)."""
    v = (value or "").strip().lower()
    if v in ("us", "usa", "usd", "united states"):
        return "us"
    return "ca"


def canonical_terms(market: str, plan_tier: Optional[str]) -> dict[str, int | str]:
    """Canonical fee terms for a tier (defaults to DEFAULT_PLAN_TIER when the
    tier id is unknown — e.g. legacy 'weekly')."""
    m = normalize_market(market)
    tier = (plan_tier or "").strip().lower()
    if tier not in PLAN_TIER_IDS:
        tier = DEFAULT_PLAN_TIER
    base = CANONICAL_FEE_TERMS[m][tier]
    return {
        "plan_tier": tier,
        "monthly_fee_cents": base["monthly_fee_cents"],
        "order_fee_cents": base["order_fee_cents"],
        "call_overage_cents_per_min": base["call_overage_cents_per_min"],
        "included_call_min": base["included_call_min"],
    }


def closest_plan_for_monthly(market: str, monthly_fee_cents: int) -> str:
    """Closest canonical tier for a custom monthly price (reps slide ABOVE a
    tier base, so proximity — not thresholds — picks the tier; mirrors the
    frontend closestMonthlyPlan)."""
    m = normalize_market(market)
    return min(
        PLAN_TIER_IDS,
        key=lambda t: abs(CANONICAL_FEE_TERMS[m][t]["monthly_fee_cents"] - int(monthly_fee_cents)),
    )


def _clamp_order_fee(market: str, plan_tier: str, fee_cents: int) -> int:
    """Clamp a negotiated per-order fee to [tier redline, tier standard rate].
    Mirrors canada.py _clamp_order_fee_cents floors."""
    base = CANONICAL_FEE_TERMS[normalize_market(market)][plan_tier]
    return max(min(int(fee_cents), int(base["order_fee_cents"])), int(base["order_fee_floor_cents"]))


def resolve_fee_terms(
    market: str,
    plan_tier: Optional[str] = None,
    monthly_fee_cents: Optional[int] = None,
    order_fee_cents: Optional[int] = None,
    call_overage_cents_per_min: Optional[int] = None,
    included_call_min: Optional[int] = None,
) -> dict[str, Any]:
    """Fill a complete fee-terms record, defaulting every omitted field from
    the selected tier's canonical values (so old clients that only send a plan
    id — or nothing at all — still lock full terms at close).

    Tier selection: explicit plan_tier wins; otherwise the closest canonical
    tier for the given monthly price; otherwise DEFAULT_PLAN_TIER.
    """
    m = normalize_market(market)
    tier = (plan_tier or "").strip().lower()
    if tier not in PLAN_TIER_IDS:
        tier = (
            closest_plan_for_monthly(m, monthly_fee_cents)
            if monthly_fee_cents else DEFAULT_PLAN_TIER
        )
    base = canonical_terms(m, tier)

    monthly = int(monthly_fee_cents) if monthly_fee_cents else int(base["monthly_fee_cents"])
    # Sanity clamp: never below the tier base, never above base + rep headroom.
    base_monthly = int(base["monthly_fee_cents"])
    monthly = max(min(monthly, base_monthly + REP_PRICE_HEADROOM_CENTS[m]), base_monthly)

    if order_fee_cents is None:
        order_fee = int(base["order_fee_cents"])
    else:
        order_fee = _clamp_order_fee(m, tier, int(order_fee_cents))

    return {
        "plan_tier": tier,
        "monthly_fee_cents": monthly,
        "order_fee_cents": order_fee,
        "call_overage_cents_per_min": (
            int(call_overage_cents_per_min)
            if call_overage_cents_per_min is not None
            else int(base["call_overage_cents_per_min"])
        ),
        "included_call_min": (
            int(included_call_min)
            if included_call_min is not None
            else int(base["included_call_min"])
        ),
    }


def terms_from_lead_row(market: str, lead: dict[str, Any]) -> dict[str, Any]:
    """Fee terms from a lead row. Locked structured columns win; any gaps
    (pre-migration rows, partially locked leads) fill from the canonical tier
    for the lead's monthly_value (dollars → cents)."""
    monthly_value = lead.get("monthly_value")
    monthly_cents = None
    try:
        if monthly_value:
            monthly_cents = int(round(float(monthly_value) * 100))
    except (TypeError, ValueError):
        monthly_cents = None
    return resolve_fee_terms(
        market,
        plan_tier=lead.get("plan_tier"),
        monthly_fee_cents=(
            int(lead["monthly_fee_cents"])
            if lead.get("monthly_fee_cents") is not None else monthly_cents
        ),
        order_fee_cents=(
            int(lead["order_fee_cents"])
            if lead.get("order_fee_cents") is not None else None
        ),
        call_overage_cents_per_min=lead.get("call_overage_cents_per_min"),
        included_call_min=lead.get("included_call_min"),
    )


# ── merchant_billing_terms access ────────────────────────────────────────────


async def get_active_terms(db, merchant_id: str) -> Optional[dict[str, Any]]:
    """The merchant's ACTIVE billing terms row, or None.

    NEVER raises — consumers sit on billing hot paths (call webhooks, renewal
    cron) and must fail open to their env defaults when this table is missing
    (migration not applied yet) or unreachable.
    """
    if not merchant_id:
        return None
    try:
        rows = await db.select(
            "merchant_billing_terms",
            filters={"merchant_id": f"eq.{merchant_id}", "superseded_at": "is.null"},
            limit=1,
        )
        return rows[0] if rows else None
    except Exception as e:  # noqa: BLE001 — fail-open by contract
        logger.warning("billing-terms lookup failed for %s (fail-open): %s", merchant_id, e)
        return None


async def set_merchant_billing_terms(
    db,
    merchant_id: str,
    terms: dict[str, Any],
    *,
    source_lead_id: Optional[str] = None,
    source_market: Optional[str] = None,
    created_by: str = "",
    override_reason: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Record new billing terms for a merchant: supersede the active row (if
    any), then insert the new one. NEVER updates terms in place — history is
    the audit trail.

    Returns the inserted row, or None on failure (caller decides whether that
    is fatal; provisioning paths treat it as loud-but-non-fatal until the
    migration is applied everywhere).
    """
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "merchant_id": merchant_id,
        "source_lead_id": source_lead_id,
        "source_market": normalize_market(source_market) if source_market else None,
        "effective_at": now,
        "created_by": created_by or "",
        "override_reason": override_reason,
        **{f: terms.get(f) for f in FEE_TERM_FIELDS},
    }
    try:
        # Supersede first: the partial unique index rejects a second active row,
        # so the insert below cannot race itself into two active contracts.
        await db.update(
            "merchant_billing_terms",
            {"superseded_at": now},
            filters={"merchant_id": f"eq.{merchant_id}", "superseded_at": "is.null"},
        )
        inserted = await db.insert("merchant_billing_terms", row)
        result = inserted[0] if inserted else row
        logger.info(
            "billing terms recorded for %s: tier=%s monthly=%s¢ order=%s¢ (lead=%s reason=%s)",
            merchant_id, row["plan_tier"], row["monthly_fee_cents"],
            row["order_fee_cents"], source_lead_id or "-", override_reason or "-",
        )
        return result
    except Exception as e:  # noqa: BLE001
        logger.error("billing terms write FAILED for %s: %s", merchant_id, e)
        return None


async def lock_lead_fee_terms(
    db, market: str, lead_id: str, terms: dict[str, Any], locked_by: str,
) -> bool:
    """Persist locked fee terms onto the lead row (canada_leads / us_leads).

    First lock wins: rows that already carry fee_terms_locked_at are not
    rewritten (the filter matches zero rows), so a retried close can't quietly
    change the contract of record. Returns True when a row was (already or
    newly) locked; False on error."""
    table = LEAD_TABLE_BY_MARKET.get(normalize_market(market), "canada_leads")
    try:
        patch = {f: terms.get(f) for f in FEE_TERM_FIELDS}
        patch["fee_terms_locked_at"] = datetime.now(timezone.utc).isoformat()
        patch["fee_terms_locked_by"] = locked_by or ""
        await db.update(
            table, patch,
            filters={"id": f"eq.{lead_id}", "fee_terms_locked_at": "is.null"},
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("lead fee-terms lock FAILED (%s %s): %s", table, lead_id, e)
        return False
