"""
Command-tier resolution for the Multi-Location Hub (and any future Command-tier
gated surface).

The repo carries two tier vocabularies (see docs/multi-location-hub-journey.md §0):

  businesses.plan_tier                 trial | starter | growth | enterprise
  merchant_billing_terms.plan_tier     standard | premium | command   (locked contract)

The sales `command` plan maps onto the account tier `enterprise`
(onboarding._PLAN_TIER_MAP). So an org is "Command tier" when EITHER:

  - its ACTIVE merchant_billing_terms row has plan_tier == 'command'
    (authoritative locked contract), OR
  - businesses.plan_tier == 'enterprise' (the provisioned account tier the sales
    `command` plan maps to).

Tier is ALWAYS resolved from the org record / billing contract server-side —
never from a request body.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("meridian.billing.tiers")

# Account-tier value (businesses.plan_tier) that the sales `command` plan maps to.
COMMAND_ACCOUNT_TIER = "enterprise"
# Billing-contract value (merchant_billing_terms.plan_tier) for the Command plan.
COMMAND_BILLING_TIER = "command"


def _is_command_value(business_plan_tier: str | None, billing_plan_tier: str | None) -> bool:
    """Pure predicate over the two tier columns — trivially unit-testable."""
    bt = (business_plan_tier or "").strip().lower()
    ct = (billing_plan_tier or "").strip().lower()
    return bt == COMMAND_ACCOUNT_TIER or ct == COMMAND_BILLING_TIER


async def resolve_org_command_tier(db, org_id: str) -> bool:
    """Return True iff ``org_id`` is on the Command tier.

    Reads businesses.plan_tier and the active merchant_billing_terms.plan_tier
    for the org. Fails CLOSED (returns False) on any lookup error — the hub gate
    must never open on ambiguity.
    """
    if not org_id:
        return False

    business_tier: str | None = None
    billing_tier: str | None = None

    try:
        biz = await db.select(
            "businesses",
            columns="plan_tier",
            filters={"id": f"eq.{org_id}"},
            limit=1,
        )
        if biz:
            business_tier = biz[0].get("plan_tier")
    except Exception as exc:  # noqa: BLE001 — fail closed, log loudly
        logger.warning("command-tier: businesses lookup failed for org=%s: %s", org_id, exc)
        return False

    # The locked contract is authoritative when present; a missing/failed lookup
    # simply leaves billing_tier None and we fall back to the account tier.
    try:
        terms = await db.select(
            "merchant_billing_terms",
            columns="plan_tier",
            filters={"merchant_id": f"eq.{org_id}", "superseded_at": "is.null"},
            limit=1,
        )
        if terms:
            billing_tier = terms[0].get("plan_tier")
    except Exception as exc:  # noqa: BLE001
        logger.warning("command-tier: billing terms lookup failed for org=%s: %s", org_id, exc)

    return _is_command_value(business_tier, billing_tier)
