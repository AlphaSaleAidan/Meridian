"""
Data Mappers — Transform Stripe API responses into Meridian database records.

Stripe is a payment processor, not a full POS: charges carry totals and payment
method but no line items, tax breakdown, or employee attribution. Each charge
maps to one `transactions` row (canonical columns — same set the Square/Clover
mappers write); `transaction_items` stays empty.

Money: Stripe amounts are already integer cents for USD/CAD — stored as-is.
"""
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid5, NAMESPACE_URL

# Same namespace as the Clover mapper so deterministic ids follow one scheme.
_ID_NS = uuid5(NAMESPACE_URL, "meridian.pos")

logger = logging.getLogger("meridian.stripe_pos.mappers")


def _stable_id(*parts: object) -> str:
    """Deterministic UUID from a natural key, so re-syncs upsert the SAME row
    (no duplicates) and distinct rows never share an id (no clobber)."""
    return str(uuid5(_ID_NS, ":".join(str(p) for p in parts)))


def _unix_to_iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()


# Stripe payment_method_details.type → Meridian payment_method enum
# (cash/card/debit/gift_card/other/unknown — see the Clover mapper).
_PAYMENT_METHOD_MAP = {
    "card": "card",
    "card_present": "card",
    "link": "card",
    "interac_present": "debit",
    "cashapp": "other",
    "us_bank_account": "other",
    "acss_debit": "other",
    "sepa_debit": "other",
    "paypal": "other",
    "klarna": "other",
    "affirm": "other",
    "afterpay_clearpay": "other",
}


class StripePOSMapper:
    """Transforms Stripe charge objects → Meridian database rows."""

    def __init__(self, org_id: str, pos_connection_id: str | None = None):
        self.org_id = org_id
        self.pos_connection_id = pos_connection_id

    def map_charge_to_transaction(self, charge: dict[str, Any]) -> dict[str, Any]:
        """
        Stripe Charge → Meridian transactions table.

          charge.id            → external_id
          charge.amount        → total_cents (already cents)
          charge.created       → transaction_at
          charge.refunded      → type 'void' (fully refunded) else 'sale'
          payment_method_details.type → payment_method
        """
        external_id = charge.get("id", "")
        amount = int(charge.get("amount", 0) or 0)
        amount_refunded = int(charge.get("amount_refunded", 0) or 0)

        pm_type = (charge.get("payment_method_details") or {}).get("type", "")
        payment_method = _PAYMENT_METHOD_MAP.get(pm_type, "card" if pm_type else "unknown")

        billing = charge.get("billing_details") or {}

        # No tax/discount/tip breakdown on a bare charge — totals only. A fully
        # refunded charge becomes a void (mirrors Clover's refunded→void); a
        # partial refund keeps the sale and records the refunded amount in
        # metadata so revenue analytics can subtract it later if needed.
        metadata: dict[str, Any] = {
            "stripe": {
                "payment_intent": charge.get("payment_intent") or None,
                "payment_method_type": pm_type or None,
            }
        }
        if amount_refunded and not charge.get("refunded"):
            metadata["stripe"]["amount_refunded_cents"] = amount_refunded
        description = charge.get("description") or ""
        if description:
            metadata["stripe"]["description"] = description[:200]

        return {
            # Deterministic from the charge's natural key so a re-sync updates
            # this row instead of churning the PK.
            "id": _stable_id(self.org_id, "stripe", external_id),
            "org_id": self.org_id,
            "location_id": None,  # Stripe has no location concept
            "external_id": external_id,
            "provider": "stripe",  # transient routing hint — stripped before write
            "transaction_at": _unix_to_iso(charge.get("created")),
            "type": "void" if charge.get("refunded") else "sale",
            "total_cents": amount,
            "subtotal_cents": amount,  # no tax breakdown available
            "tax_cents": 0,
            "discount_cents": 0,
            "tip_cents": 0,
            "payment_method": payment_method,
            "metadata": metadata,
            "employee_name": "",
            "employee_external_id": "",
            "customer_id": charge.get("customer") or None,
            "customer_email": billing.get("email") or charge.get("receipt_email") or None,
            "currency": (charge.get("currency") or "").upper() or None,
        }
