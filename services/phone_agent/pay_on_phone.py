"""
PAY ON THE PHONE — anti-scam payment collection for the voice agent.

The order is created in the POS as an OPEN/unpaid order, but the *kitchen ticket
is held* (no staff SMS, status `awaiting_payment`) until the caller pays via a
secure link texted to their phone. Payment confirmation (Square webhook, or a
demo-mode simulation) flips the order to `paid` and releases the ticket.

This reuses the existing payment plumbing unchanged:
  payment_links.create_payment_link  → Square/Toast/Clover/Meridian checkout URL
  sms_checkout.send_checkout_sms      → texts the link to caller_info["phone"]

PCI-safe by construction: card data never touches us — Square/Apple Pay/Google
Pay handle it on the hosted link. DTMF keypad capture is a deliberately-OFF
stretch (see PHONE_DTMF_PAYMENT below).
"""
import logging
import os
from typing import Any

import httpx

from merchant_config import MerchantPhoneConfig
from payment_links import create_checkout
from sms_checkout import send_checkout_sms
from order_router import route_order

logger = logging.getLogger("meridian.phone_agent.pay_on_phone")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# Writes need the service-role key (anon lacks INSERT/UPDATE GRANT on phone_orders).
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

# Demo-safe: never take a real charge in demo/synthetic. When on, the pay-now
# path simulates an immediate "paid" so the full flow is demonstrable end to end.
DEMO_MERCHANT_ID = os.getenv("DEMO_MERCHANT_ID", "demo-merchant")

# ponytail: DTMF keypad card entry is a PCI-heavy stretch — kept OFF by default.
# When eventually built it must run through a PCI-DSS-compliant DTMF masking
# provider (e.g. Telnyx/Twilio <Pay> or a tokenizing IVR), NOT raw digit capture.
# The texted secure link is the primary, recommended path; this flag only exists
# so the wiring point is explicit.
DTMF_PAYMENT_ENABLED = os.getenv("PHONE_DTMF_PAYMENT", "0").lower() in ("1", "true", "yes")


def is_demo(merchant_id: str) -> bool:
    """Demo/synthetic merchant → simulate payment, never charge."""
    return merchant_id == DEMO_MERCHANT_ID


def resolve_mode(config: MerchantPhoneConfig, pay_choice: str = "") -> str:
    """Resolve the effective payment path for this order. `optional` defers to
    the caller's pay_choice (defaults to pay_now if unset/invalid)."""
    mode = getattr(config, "payment_mode", "pay_now")
    if mode == "optional":
        choice = (pay_choice or "").strip().lower()
        return choice if choice in ("pay_now", "pay_at_pickup") else "pay_now"
    return mode if mode in ("pay_now", "pay_at_pickup") else "pay_now"


async def dispatch_order(
    order: dict[str, Any],
    config: MerchantPhoneConfig,
    caller_info: dict,
    pos_result: dict,
    pay_choice: str = "",
) -> dict:
    """Post-POS dispatch shared by the live bot and the tests.

    Branches on the resolved payment mode:
      pay_now      → hold the kitchen ticket, text a secure pay link (anti-scam)
      pay_at_pickup → today's behavior: release to the kitchen via route_order

    Returns {"mode", "released", ...collect_pay_now fields}.
    """
    mode = resolve_mode(config, pay_choice)
    if mode == "pay_now":
        result = await collect_pay_now(order, config, caller_info, pos_result)
        result["mode"] = "pay_now"
        result["released"] = False  # held until paid
        return result
    # pay_at_pickup — release to kitchen now (unchanged legacy path).
    await route_order(order, config, caller_info, pos_result)
    return {"mode": "pay_at_pickup", "released": True}


async def collect_pay_now(
    order: dict[str, Any],
    config: MerchantPhoneConfig,
    caller_info: dict,
    pos_result: dict,
) -> dict:
    """
    Pay-now path: create the Square payment link (order already OPEN in POS),
    text it to the caller, and write the phone_orders row as `awaiting_payment`
    with `payment_status='pending'` — the kitchen ticket is HELD until paid.

    Returns {"payment_link", "sms_sent", "method", "simulated_paid"}.
    """
    phone = caller_info.get("phone") or order.get("caller_phone", "")
    order["caller_phone"] = phone

    # Unified entry: routes to Stripe Connect when the merchant is onboarded for
    # it (flag-gated), else falls back to the per-POS payment link unchanged.
    payment_result = await create_checkout(
        order, config, pos_result.get("pos_order_id", ""),
    )

    sms_result: dict = {}
    if payment_result.get("url"):
        sms_result = await send_checkout_sms(
            order=order,
            payment_link=payment_result["url"],
            business_name=config.business_name,
            sms_pay_template=getattr(config, "sms_pay_template", "") or "",
        )

    # Write the held order: pending payment, ticket NOT released to the kitchen.
    await _save_held_order(order, pos_result, payment_result, sms_result)

    simulated_paid = False
    if is_demo(config.merchant_id):
        # Demo-safe: no real charge possible, so simulate "paid" immediately so
        # the release path is demonstrable on a synthetic call.
        await mark_order_paid(
            config.merchant_id, phone,
            pos_order_id=pos_result.get("pos_order_id", ""),
            simulate=True,
        )
        simulated_paid = True

    logger.info(
        "Pay-now: merchant=%s phone=%s link=%s sms=%s held=awaiting_payment sim_paid=%s",
        config.merchant_id, phone,
        payment_result.get("method", "none"),
        "sent" if sms_result.get("sent") else "not_sent",
        simulated_paid,
    )

    return {
        "payment_link": payment_result.get("url", ""),
        "sms_sent": sms_result.get("sent", False),
        "method": payment_result.get("method", "none"),
        "simulated_paid": simulated_paid,
    }


async def _save_held_order(
    order: dict, pos_result: dict, payment_result: dict, sms_result: dict
) -> None:
    """Insert the phone_orders row in the HELD state (anti-scam): the order is
    created but `status='awaiting_payment'` and `kitchen_released=false`, so the
    kitchen ticket / staff SMS is NOT sent until payment confirms."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
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
        "pos_order_id": pos_result.get("pos_order_id", ""),
        "pos_success": pos_result.get("success", False),
        "source": "phone_agent",
        # anti-scam: held until paid
        "status": "awaiting_payment",
        "kitchen_released": False,
        "payment_status": "pending",
        "payment_link": payment_result.get("url", ""),
        "payment_method": payment_result.get("method", ""),
        "sms_sent": sms_result.get("sent", False),
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/phone_orders",
                json=row,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                timeout=10,
            )
    except Exception as e:
        logger.error("Failed to save held order: %s", e)


async def mark_order_paid(
    merchant_id: str,
    caller_phone: str = "",
    pos_order_id: str = "",
    simulate: bool = False,
    method: str = "",
    card_brand: str = "",
    card_last4: str = "",
    payment_txn_id: str = "",
) -> dict:
    """Payment confirmed → flip the held order to paid AND release the kitchen
    ticket. Matches by pos_order_id when known (most precise), else by
    merchant+phone (latest). Idempotent.

    `method`/`card_*`/`payment_txn_id` record HOW it was paid (e.g. the
    card-on-phone keypad fallback) so the order/receipt shows brand + last-4.
    Only the last-4 is ever stored — never the full PAN.

    Returns {"released": bool, "matched_by": str}.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.info(
            "mark_order_paid (no Supabase): merchant=%s phone=%s pos_order=%s simulate=%s method=%s",
            merchant_id, caller_phone, pos_order_id, simulate, method or "link",
        )
        return {"released": True, "matched_by": "none"}

    if pos_order_id:
        query = f"?pos_order_id=eq.{pos_order_id}"
        matched_by = "pos_order_id"
    elif merchant_id and caller_phone:
        query = (
            f"?merchant_id=eq.{merchant_id}&caller_phone=eq.{caller_phone}"
            f"&order=created_at.desc&limit=1"
        )
        matched_by = "merchant_phone"
    else:
        logger.warning("mark_order_paid: no key to match an order")
        return {"released": False, "matched_by": "none"}

    patch = {
        "payment_status": "paid",
        "status": "paid",
        "kitchen_released": True,
    }
    if method:
        patch["payment_method"] = method
    if card_brand:
        patch["card_brand"] = card_brand
    if card_last4:
        patch["card_last4"] = card_last4
    if payment_txn_id:
        patch["payment_txn_id"] = payment_txn_id
    if simulate:
        patch["payment_note"] = "simulated (demo)"
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/phone_orders{query}",
                json=patch,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                timeout=10,
            )
        logger.info("Order paid + kitchen released (matched_by=%s)", matched_by)
        return {"released": True, "matched_by": matched_by}
    except Exception as e:
        logger.error("mark_order_paid failed: %s", e)
        return {"released": False, "matched_by": matched_by}
