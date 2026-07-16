"""
Pre-invoice fee reconciliation — "is every live merchant billed what they signed?"

Diffs the CONTRACTED terms (merchant_billing_terms active row, falling back to
the closed lead's locked terms matched by business email) against what is
ACTUALLY APPLIED in live billing:

  monthly_fee_cents           subscriptions.monthly_price_cents
  order_fee_cents             phone_agent_config.order_fee_cents, else the
                              MERIDIAN_SERVICE_FEE_CENTS env default
  call_overage_cents_per_min  merchant terms when present, else env default
  included_call_min           merchant terms when present, else env default
  website_order_fee_cents     merchant_websites.ordering_fee_pct applied to a
                              standard $30 order (percentage model), compared
                              against the contracted flat per-order fee —
                              informational: the two fee models differ, so any
                              delta here means the website rail runs a
                              different economics than the deal.

Zero mismatches = healthy. `check_merchant` is the lightweight guard hook the
charge paths call as a log-warning pre-check (warn, don't block — v1).
Everything here is read-only and fail-open: a reconciliation failure must
never break billing.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from .fee_terms import (
    DEFAULT_CALL_OVERAGE_CENTS_PER_MIN,
    DEFAULT_INCLUDED_CALL_MIN,
    get_active_terms,
    terms_from_lead_row,
)

logger = logging.getLogger("meridian.billing.fee_reconciliation")

# Reference order subtotal for expressing the % website fee in cents.
STANDARD_ORDER_SUBTOTAL_CENTS = 3000

_SUB_STATUSES = ("active", "trialing", "pending_payment")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except (TypeError, ValueError):
        return default


def diff_terms(merchant_id: str, contracted: dict[str, Any], applied: dict[str, Any]) -> list[dict[str, Any]]:
    """Pure diff of contracted vs applied fee values.

    Returns [{merchant_id, field, contracted, applied, delta}] for every field
    present (non-None) on BOTH sides that disagrees. delta = applied −
    contracted (positive ⇒ merchant is being OVERBILLED on that field).
    """
    mismatches: list[dict[str, Any]] = []
    for field in sorted(set(contracted) | set(applied)):
        c, a = contracted.get(field), applied.get(field)
        if c is None or a is None:
            continue
        try:
            c_i, a_i = int(c), int(a)
        except (TypeError, ValueError):
            if str(c) != str(a):
                mismatches.append({"merchant_id": merchant_id, "field": field,
                                   "contracted": c, "applied": a, "delta": None})
            continue
        if c_i != a_i:
            mismatches.append({"merchant_id": merchant_id, "field": field,
                               "contracted": c_i, "applied": a_i, "delta": a_i - c_i})
    return mismatches


async def _contracted_terms(db, merchant_id: str) -> tuple[Optional[dict[str, Any]], str]:
    """(contracted terms, source) — 'terms' | 'lead' | 'none'."""
    terms = await get_active_terms(db, merchant_id)
    if terms:
        return terms, "terms"
    # Fallback: closed lead matched by the business's email. This linkage is
    # exactly what merchant_billing_terms formalizes; the fallback exists for
    # merchants provisioned before this system.
    try:
        biz = await db.select("businesses", "id,email",
                              filters={"id": f"eq.{merchant_id}"}, limit=1)
        email = (biz[0].get("email") or "").strip().lower() if biz else ""
        if email:
            for market, table in (("ca", "canada_leads"), ("us", "us_leads")):
                leads = await db.select(
                    table,
                    filters={"contact_email": f"ilike.{email}",
                             "stage": "in.(closed_won,customer_walkthrough)"},
                    order="updated_at.desc", limit=1,
                )
                if leads:
                    return terms_from_lead_row(market, leads[0]), "lead"
    except Exception as e:  # noqa: BLE001
        logger.warning("lead-fallback lookup failed for %s: %s", merchant_id, e)
    return None, "none"


async def _applied_terms(db, merchant_id: str, subscription: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """What live billing would actually charge this merchant today."""
    applied: dict[str, Any] = {
        "call_overage_cents_per_min": _env_int("MERIDIAN_VOICE_OVERAGE_CENTS_PER_MIN",
                                               DEFAULT_CALL_OVERAGE_CENTS_PER_MIN),
        "included_call_min": _env_int("MERIDIAN_VOICE_INCLUDED_MIN", DEFAULT_INCLUDED_CALL_MIN),
        "order_fee_cents": _env_int("MERIDIAN_SERVICE_FEE_CENTS", 0),
    }
    try:
        if subscription is None:
            subs = await db.select(
                "subscriptions",
                filters={"org_id": f"eq.{merchant_id}",
                         "status": f"in.({','.join(_SUB_STATUSES)})"},
                limit=1,
            )
            subscription = subs[0] if subs else None
        if subscription and subscription.get("monthly_price_cents") is not None:
            applied["monthly_fee_cents"] = int(subscription["monthly_price_cents"])
    except Exception as e:  # noqa: BLE001
        logger.warning("subscription lookup failed for %s: %s", merchant_id, e)

    try:
        pac = await db.select("phone_agent_config", "order_fee_cents,plan_tier",
                              filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
        if pac:
            if pac[0].get("order_fee_cents") is not None:
                applied["order_fee_cents"] = int(pac[0]["order_fee_cents"])
            if pac[0].get("plan_tier"):
                applied["plan_tier"] = str(pac[0]["plan_tier"]).strip().lower()
    except Exception as e:  # noqa: BLE001
        logger.warning("phone_agent_config lookup failed for %s: %s", merchant_id, e)

    try:
        sites = await db.select("merchant_websites", "ordering_fee_pct,ordering_enabled",
                                filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
        if sites and sites[0].get("ordering_enabled"):
            pct = float(sites[0].get("ordering_fee_pct") or 0.0299)
            applied["website_order_fee_cents"] = int(round(STANDARD_ORDER_SUBTOTAL_CENTS * pct))
    except Exception as e:  # noqa: BLE001
        logger.warning("merchant_websites lookup failed for %s: %s", merchant_id, e)

    return applied


def _comparable_contracted(contracted: dict[str, Any]) -> dict[str, Any]:
    """Project contracted terms onto the applied field space."""
    out = {k: contracted.get(k) for k in (
        "plan_tier", "monthly_fee_cents", "order_fee_cents",
        "call_overage_cents_per_min", "included_call_min",
    )}
    # The website rail is compared against the same contracted per-order fee.
    if contracted.get("order_fee_cents") is not None:
        out["website_order_fee_cents"] = contracted["order_fee_cents"]
    return out


async def check_merchant(db, merchant_id: str) -> list[dict[str, Any]]:
    """Guard hook for invoice/charge paths: contracted-vs-applied mismatches
    for one merchant. [] = healthy OR no contracted source (nothing to check).
    Fail-open: any internal error returns []."""
    try:
        contracted, source = await _contracted_terms(db, merchant_id)
        if not contracted:
            return []
        applied = await _applied_terms(db, merchant_id)
        mismatches = diff_terms(merchant_id, _comparable_contracted(contracted), applied)
        for m in mismatches:
            m["contract_source"] = source
        return mismatches
    except Exception as e:  # noqa: BLE001
        logger.warning("check_merchant failed for %s (fail-open): %s", merchant_id, e)
        return []


async def reconcile_all(db) -> dict[str, Any]:
    """Full pre-invoice reconciliation across every merchant with a live
    subscription. Zero mismatches = healthy."""
    subs = await db.select(
        "subscriptions",
        filters={"status": f"in.({','.join(_SUB_STATUSES)})"},
    )
    matched: list[str] = []
    mismatched: list[dict[str, Any]] = []
    unlinked: list[str] = []

    for sub in subs or []:
        merchant_id = sub.get("org_id") or ""
        if not merchant_id:
            continue
        contracted, source = await _contracted_terms(db, merchant_id)
        if not contracted:
            unlinked.append(merchant_id)
            continue
        applied = await _applied_terms(db, merchant_id, subscription=sub)
        diffs = diff_terms(merchant_id, _comparable_contracted(contracted), applied)
        if diffs:
            mismatched.append({
                "merchant_id": merchant_id,
                "contract_source": source,
                "subscription_status": sub.get("status"),
                "mismatches": diffs,
                "monthly_delta_cents": next(
                    (d["delta"] for d in diffs
                     if d["field"] == "monthly_fee_cents" and d["delta"] is not None), 0),
            })
        else:
            matched.append(merchant_id)

    return {
        "healthy": not mismatched,
        "checked": len(matched) + len(mismatched) + len(unlinked),
        "matched": matched,
        "mismatched": mismatched,
        "unlinked": unlinked,
        "total_monthly_delta_cents": sum(m["monthly_delta_cents"] for m in mismatched),
    }
