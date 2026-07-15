"""
Square Kitchen Submitter — lands a Meridian mobile order in a merchant's
Square POS the way a real ticket does: a Square Order at their location with
line items (per-item notes), a PICKUP/DELIVERY fulfillment (what makes the
order show on Square's Orders screen / KDS and drive kitchen printing), the
Meridian source name, and a fulfillment note carrying the payment state.

The generic REST connector can't produce a valid Square CreateOrder body —
Square needs location_id, string quantities, Money objects, and a fulfillment
with a scheduled time. Ported from the proven phone-sidecar Square path.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger("meridian.pos.square_kitchen")

SQUARE_VERSION = "2024-01-18"
_TIMEOUT = 15


def square_api_base() -> str:
    """SQUARE_ENVIRONMENT=sandbox targets Square's sandbox host, mirroring the
    Clover submitter's env contract."""
    if os.environ.get("SQUARE_ENVIRONMENT", "").strip().lower() == "sandbox":
        return "https://connect.squareupsandbox.com"
    return "https://connect.squareup.com"


def _pay_line(order: dict) -> str:
    paid = order.get("status") == "paid" or bool(order.get("paid"))
    return "PAID ONLINE (Stripe) — do not collect" if paid else "UNPAID, collect in store"


async def submit_square_kitchen_order(
    *,
    access_token: str,
    location_id: str,
    order: dict,
    source_tag: str = "Meridian Mobile Order",
) -> dict:
    """Create the order in Square. Returns {success, pos_order_id, reason?}.

    The idempotency key is derived from the Meridian order id, so webhook
    retries that reach this far can never create a second Square order.
    """
    if not (access_token or "").strip():
        return {"success": False, "reason": "missing_square_token"}
    if not (location_id or "").strip():
        return {"success": False, "reason": "square_missing_location_id"}

    currency = (order.get("currency") or "USD").upper()
    order_ref = str(order.get("order_ref") or order.get("id") or "")

    line_items = []
    for item in order.get("items", []):
        unit_price = float(item.get("price", item.get("unit_price", 0)) or 0)
        special = (item.get("special_instructions") or item.get("notes") or "").strip()
        li = {
            "name": str(item.get("name", "Item"))[:512],
            "quantity": str(_safe_qty(item)),
            "base_price_money": {
                "amount": int(round(unit_price * 100)),
                "currency": currency,
            },
        }
        if special:
            li["note"] = special[:500]
        line_items.append(li)

    customer = (order.get("customer_name") or "").strip() or "Mobile Order"
    phone = (order.get("customer_phone") or order.get("caller_phone") or "").strip()
    recipient = {"display_name": customer}
    if phone:
        recipient["phone_number"] = phone

    note = f"{source_tag} #{order_ref[:8].upper()} • {_pay_line(order)}"
    extra = (order.get("special_instructions") or "").strip()
    if extra:
        note = f"{note} • {extra}"
    note = note[:500]

    # Square requires a scheduled time per fulfillment type (else 400). ASAP.
    now = datetime.now(timezone.utc)
    if (order.get("order_type") or "pickup").lower() == "delivery":
        fulfillment = {
            "type": "DELIVERY",
            "state": "PROPOSED",
            "delivery_details": {
                "recipient": {
                    **recipient,
                    "address": {"address_line_1": order.get("delivery_address", "")
                                or "Address on order"},
                },
                "schedule_type": "ASAP",
                "deliver_at": (now + timedelta(minutes=45)).isoformat(),
                "note": note,
            },
        }
    else:
        fulfillment = {
            "type": "PICKUP",
            "state": "PROPOSED",
            "pickup_details": {
                "recipient": recipient,
                "schedule_type": "ASAP",
                "pickup_at": (now + timedelta(minutes=15)).isoformat(),
                "note": note,
            },
        }

    payload = {
        "idempotency_key": f"mmo-{order_ref}"[:45] or "mmo-unknown",
        "order": {
            "location_id": location_id,
            "reference_id": order_ref[:40],
            "source": {"name": source_tag},
            "line_items": line_items,
            "fulfillments": [fulfillment],
        },
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.post(
            f"{square_api_base()}/v2/orders",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Square-Version": SQUARE_VERSION,
            },
        )
    if res.status_code == 200:
        pos_order_id = (res.json().get("order") or {}).get("id", "")
        return {"success": True, "pos_order_id": pos_order_id}
    logger.warning("square kitchen: create failed HTTP %s: %s",
                   res.status_code, res.text[:300])
    return {"success": False, "reason": f"square_http_{res.status_code}"}


def _safe_qty(item: dict) -> int:
    try:
        return max(1, min(int(item.get("quantity", 1)), 99))
    except (TypeError, ValueError):
        return 1
