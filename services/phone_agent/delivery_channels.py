"""
Delivery-channel fan-out primitives for phone-agent orders.

An order has up to three delivery legs, run in PARALLEL (not either/or):

  pos           → ticket pushed into the merchant's POS (pos_connector)
  customer_sms  → order confirmation + payment link texted to the caller
  merchant_sms  → order summary texted to the merchant's line (transfer_number)
                  so a merchant WITHOUT a connected POS still hears about the
                  order, and a merchant WITH one gets a belt-and-braces alert.

Per-merchant override lives in phone_agent_config.delivery_channels (JSONB,
e.g. {"pos": true, "customer_sms": true, "merchant_sms": false}); missing
keys / NULL default to enabled. Each leg's outcome is recorded on the
phone_orders row (pos_delivery_status / sms_delivery_status /
merchant_notify_status + delivery_detail) so support can see exactly what
fired and what failed.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import httpx

logger = logging.getLogger("meridian.phone_agent.delivery")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# Writes need the service-role key (anon lacks INSERT GRANT on phone_orders).
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

# Fan-out default: every channel on. A missing/NULL delivery_channels column
# must behave exactly like this dict.
DEFAULT_CHANNELS = {"pos": True, "customer_sms": True, "merchant_sms": True}

# Statuses
SENT = "sent"
FAILED = "failed"
DEFERRED = "deferred_pending_payment"
SKIPPED_DISABLED = "skipped_disabled"
SKIPPED_NO_POS = "skipped_no_pos"
SKIPPED_NO_PHONE = "skipped_no_phone"
SKIPPED_NO_NUMBER = "skipped_no_number"
SKIPPED_NO_LINK = "skipped_no_link"


def resolve_channels(config) -> dict[str, bool]:
    """Effective delivery-channel toggles for a merchant.

    Reads config.delivery_channels (dict or None). Only explicit booleans
    override the defaults — junk values and missing keys stay enabled, so a
    partially-set column can never silently kill a delivery leg.
    """
    out = dict(DEFAULT_CHANNELS)
    raw = getattr(config, "delivery_channels", None)
    if isinstance(raw, dict):
        for key in out:
            if isinstance(raw.get(key), bool):
                out[key] = raw[key]
    return out


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def leg_outcome(status: str, error: str = "", **extra: Any) -> dict:
    """Uniform per-leg outcome record: {"status", "at", "error"?, ...}."""
    out: dict[str, Any] = {"status": status, "at": _now_iso()}
    if error:
        out["error"] = error
    out.update(extra)
    return out


async def run_legs(
    legs: dict[str, Callable[[], Awaitable[dict]]],
) -> dict[str, dict]:
    """Run delivery legs concurrently with per-leg exception isolation.

    Each callable returns a leg-outcome dict (see leg_outcome). A leg that
    raises is recorded as FAILED with the exception text — it can never take
    a sibling leg down with it.
    """
    names = list(legs)
    results = await asyncio.gather(
        *(legs[name]() for name in names), return_exceptions=True
    )
    out: dict[str, dict] = {}
    for name, res in zip(names, results):
        if isinstance(res, BaseException):
            logger.error("delivery leg %r raised: %s", name, res)
            out[name] = leg_outcome(FAILED, error=str(res) or type(res).__name__)
        else:
            out[name] = res
    return out


def delivery_columns(outcomes: dict[str, dict]) -> dict:
    """Map leg outcomes onto the phone_orders per-channel columns."""
    detail = {name: dict(o) for name, o in outcomes.items()}
    return {
        "pos_delivery_status": (outcomes.get("pos") or {}).get("status"),
        "sms_delivery_status": (outcomes.get("customer_sms") or {}).get("status"),
        "merchant_notify_status": (outcomes.get("merchant_sms") or {}).get("status"),
        "delivery_detail": detail,
    }


# ─── phone_orders persistence ────────────────────────────────────────────────


def base_order_row(order: dict, pos_result: dict) -> dict:
    """Common phone_orders insert fields shared by held + released orders.

    The full pos_result (incl. Clover's kitchen_fired / kitchen_fire_status)
    also lands verbatim in delivery_detail.pos.pos_result via pos_outcome, so
    support always sees whether the printer actually fired.
    """
    row = {
        "merchant_id": order.get("merchant_id", ""),
        "customer_name": order.get("customer_name", ""),
        "order_type": order.get("order_type", "pickup"),
        "items": order.get("items", []),
        "subtotal": order.get("subtotal", 0),
        "tax": order.get("tax", 0),
        "total": order.get("total", 0),
        "delivery_address": order.get("delivery_address", ""),
        "special_requests": order.get("special_requests", ""),
        "caller_phone": order.get("caller_phone", ""),
        "pos_system": order.get("pos_system", ""),
        "pos_order_id": (pos_result or {}).get("pos_order_id", ""),
        "pos_success": (pos_result or {}).get("success", False),
        # test orders mark themselves so dashboards/support can filter them
        "source": order.get("source", "phone_agent"),
    }
    if (pos_result or {}).get("kitchen_fired"):
        # Clover print_event accepted: the ticket fired to the order printer.
        # (Read-back verification — pos_fulfillment — may later overwrite this
        # with the confirmed POS state, which is strictly stronger evidence.)
        row["fulfillment_state"] = "kitchen_fired"
    return row


async def save_order_row(row: dict) -> str | None:
    """Insert a phone_orders row; returns the new row id (or None)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/phone_orders",
                json=row,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    # representation so callers (test orders, fulfillment
                    # verification) get the row id back for follow-up updates.
                    "Prefer": "return=representation",
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                body = resp.json()
                if isinstance(body, list) and body:
                    return body[0].get("id")
            else:
                logger.error("phone_orders insert failed %d: %s",
                             resp.status_code, resp.text[:300])
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to save phone order: %s", e)
    return None


# ─── Leg implementations ─────────────────────────────────────────────────────
# Imports inside the legs are late (module-level sibling imports, same style as
# the rest of services/phone_agent) so tests can monkeypatch and so importing
# this module never drags in HTTP plumbing.


async def create_pos_for_config(order: dict, config, pos_result: dict | None = None) -> dict:
    """POS create with the merchant's creds (env fallback for the Square demo,
    same rule as bot.py / the Vapi route), honoring the per-merchant demo_safe
    guard. A `pos_result` passed by legacy callers that already created the
    order is honored unchanged."""
    if pos_result is not None:
        return pos_result
    import os

    from pos_connector import create_pos_order
    pos_system = getattr(config, "pos_system", "") or ""
    token = getattr(config, "pos_access_token", "") or ""
    location = getattr(config, "pos_location_id", "") or ""
    if pos_system == "square" and not token:
        token = os.getenv("SQUARE_ACCESS_TOKEN", "")
        location = location or os.getenv("SQUARE_LOCATION_ID", "")
    return await create_pos_order(
        order, pos_system, token, location,
        demo_safe=bool(getattr(config, "demo_safe", False)),
    )


def pos_outcome(pos_result: dict, *, already_created: bool = False) -> dict:
    """Map a pos_connector result onto a leg outcome."""
    pos_result = pos_result or {}
    extra = {"pos_result": pos_result}
    if already_created:
        extra["already_created"] = True
    if pos_result.get("success"):
        return leg_outcome(SENT, **extra)
    reason = pos_result.get("reason", "") or "pos_failed"
    if reason == "demo_safe":
        # Guarded, not failed: demo/test merchants are logs-only by design.
        return leg_outcome("demo_safe", **extra)
    if reason == "no_pos_configured":
        return leg_outcome(SKIPPED_NO_POS, **extra)
    if reason == "pos_orders_disabled":
        return leg_outcome(SKIPPED_DISABLED, error="pos_orders_disabled", **extra)
    return leg_outcome(FAILED, error=str(pos_result.get("error") or reason), **extra)


async def pos_delivery_leg(order: dict, config, pos_result: dict | None = None) -> dict:
    """POS push leg: create the ticket in the merchant's POS now."""
    try:
        result = await create_pos_for_config(order, config, pos_result)
    except Exception as e:  # noqa: BLE001 — leg isolation, never raise
        return leg_outcome(FAILED, error=str(e),
                           pos_result={"success": False, "reason": "exception"})
    return pos_outcome(result, already_created=pos_result is not None)


async def customer_sms_leg(order: dict, config) -> dict:
    """Customer SMS leg: payment link / order confirmation to the caller.

    NOTE: runs in parallel with the POS leg, so the checkout is created without
    a pos_order_id (same as the deferred pay_now path); payment matching falls
    back to merchant+phone.
    """
    from payment_links import create_checkout
    from sms_checkout import send_checkout_sms

    phone = order.get("caller_phone", "")
    if not phone:
        return leg_outcome(SKIPPED_NO_PHONE)
    if not getattr(config, "sms_checkout_enabled", True):
        return leg_outcome(SKIPPED_DISABLED)

    payment_result = await create_checkout(order, config, "")
    url = payment_result.get("url", "")
    if not url:
        return leg_outcome(SKIPPED_NO_LINK,
                           method=payment_result.get("method", "none"))
    sms_result = await send_checkout_sms(
        order=order,
        payment_link=url,
        business_name=getattr(config, "business_name", "") or "",
        sms_pay_template=getattr(config, "sms_pay_template", "") or "",
    )
    if sms_result.get("sent"):
        return leg_outcome(SENT, payment_link=url,
                           method=payment_result.get("method", ""))
    return leg_outcome(FAILED, error=str(sms_result.get("reason", "sms_failed")),
                       payment_link=url, method=payment_result.get("method", ""))


async def merchant_sms_leg(order: dict, config, body: str | None = None) -> dict:
    """Merchant notification leg: text the order ticket to the merchant's line
    (transfer_number) so the order is heard about even when no POS is connected."""
    from order_router import _format_order_summary
    from sms_checkout import send_sms

    number = (getattr(config, "transfer_number", "") or "").strip()
    if not number:
        return leg_outcome(SKIPPED_NO_NUMBER)
    text = body or _format_order_summary(order)
    result = await send_sms(number, text)
    if result.get("sent"):
        return leg_outcome(SENT, to=number)
    return leg_outcome(FAILED, error=str(result.get("reason", "sms_failed")), to=number)


# ─── Test order (kitchen prove-out) ──────────────────────────────────────────

TEST_ORDER_CUSTOMER = "MERIDIAN TEST ORDER"
TEST_ORDER_NOTE = (
    "TEST — do not make. Sent from Meridian setup to verify order delivery. "
    "Please delete this ticket."
)


def build_test_order(config) -> dict:
    """A clearly-marked test order in the normalized-order shape.

    Uses the merchant's cheapest priced menu item (so the ticket exercises a
    REAL item their kitchen recognizes) or a $0.01 line when no priced menu is
    configured. Runs through the SAME dispatch path as a live call.
    """
    item_name, unit_price = "Meridian Test Item", 0.01
    priced = [
        m for m in (getattr(config, "menu_items", None) or [])
        if isinstance(m, dict) and (m.get("name") or "").strip()
        and isinstance(m.get("price"), (int, float)) and m["price"] > 0
    ]
    if priced:
        cheapest = min(priced, key=lambda m: float(m["price"]))
        item_name, unit_price = cheapest["name"], round(float(cheapest["price"]), 2)

    # Same currency derivation as order_normalizer.normalize_order.
    currency = (getattr(config, "currency", None) or "").lower()
    if not currency:
        country = (getattr(config, "country", "") or "").upper()
        language = (getattr(config, "language", "") or "").lower()
        currency = "cad" if country in ("CA", "CAN", "CANADA") or language == "fr" else "usd"

    return {
        "merchant_id": config.merchant_id,
        "business_name": getattr(config, "business_name", "") or "",
        "customer_name": TEST_ORDER_CUSTOMER,
        "order_type": "pickup",
        "items": [{
            "name": item_name,
            "quantity": 1,
            "size": "",
            "unit_price": unit_price,
            "modifier_total": 0.0,
            "line_total": unit_price,
            "modifications": [],
            "special_instructions": TEST_ORDER_NOTE,
            "matched_menu_item": bool(priced),
        }],
        "unavailable_items": [],
        # Deliberately untaxed: the point is proving delivery, not money math.
        "subtotal": unit_price,
        "tax": 0.0,
        "total": unit_price,
        "currency": currency,
        "delivery_address": "",
        "special_requests": TEST_ORDER_NOTE,
        "caller_phone": "",
        "source": "test_order",
        "pos_system": getattr(config, "pos_system", "") or "",
    }
