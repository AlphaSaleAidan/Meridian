"""
Shared customer order-receipt SMS — ONE code path for every phone order.

Both the turn-based Vapi path and the streaming Pipecat path complete orders and
owe the caller the same confirmation receipt ("your order is confirmed"). Before
this module the receipt was duplicated across the Stripe / Clover / pay-redirect
payment webhooks (pay_now only) and never fired at all for pay_at_pickup orders
or for streaming orders released without a payment webhook. This helper is the
single sender they all call.

Guarantees:
  * IDEMPOTENT on the order id. The durable guard is a conditional PATCH on
    phone_orders.receipt_sent (see _claim_receipt): the first caller to flip
    false→true owns the send; every later caller (sidecar AND webhook both
    reporting the same order) gets already_sent and sends nothing. When Supabase
    is unconfigured (tests / demo box) an in-process set stands in so a single
    process still never double-sends.
  * Respects the transactional opt-out (casl_compliance.fetch_optout_status) —
    a STOP that set transactional_optout kills the receipt.
  * Respects the killswitch env PHONE_RECEIPT_SMS_ENABLED (default on) so the
    receipt can be cut fleet-wide without a deploy.

Result: {"sent": bool, "reason"?: str, "order_id": str}.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from casl_compliance import fetch_optout_status
from sms_checkout import send_sms

logger = logging.getLogger("meridian.phone_agent.order_receipt")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# Writes need the service-role key (anon lacks UPDATE grant on phone_orders).
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

# In-process idempotency backstop for when Supabase is unconfigured (tests, the
# demo box) — a single process still never double-sends the same order id.
_sent_ids: set[str] = set()


def _killswitch_on() -> bool:
    """Receipt SMS enabled? Read at call time so the flag can be flipped without
    a restart. Default ON — only an explicit 0/false/no disables it."""
    return os.getenv("PHONE_RECEIPT_SMS_ENABLED", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


async def _claim_receipt(order_id: str) -> bool:
    """Durable, cross-worker idempotency claim.

    Conditionally flip phone_orders.receipt_sent false→true for this order id and
    return whether THIS caller won the race (i.e. is responsible for sending).
    PostgREST returns the updated rows with Prefer: return=representation — a
    non-empty list means we flipped it (we send); an empty list means another
    caller already claimed it (we skip). The filter receipt_sent=is.false makes
    the flip atomic at the row level.

    When Supabase is unconfigured, fall back to the in-process set so a single
    process still never double-sends.
    """
    if not order_id:
        return False
    if not SUPABASE_URL or not SUPABASE_KEY:
        if order_id in _sent_ids:
            return False
        _sent_ids.add(order_id)
        return True
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/phone_orders"
                f"?pos_order_id=eq.{order_id}&receipt_sent=is.false",
                json={"receipt_sent": True},
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                timeout=10,
            )
        if resp.status_code >= 300:
            # A missing receipt_sent column (migration not applied) must NOT
            # strand the receipt — degrade to the in-process guard so the SMS
            # still fires (at-most-once within a process).
            logger.warning("receipt claim PATCH %s: %s — degrading to in-proc guard",
                           resp.status_code, resp.text[:200])
            if order_id in _sent_ids:
                return False
            _sent_ids.add(order_id)
            return True
        rows = resp.json() if resp.content else []
        return bool(rows)
    except Exception as e:  # noqa: BLE001 — never strand the receipt on a claim hiccup
        logger.warning("receipt claim failed for %s: %s — degrading to in-proc guard", order_id, e)
        if order_id in _sent_ids:
            return False
        _sent_ids.add(order_id)
        return True


def _format_receipt(order: dict[str, Any], config, *, paid: bool,
                    amount_cents: int | None, currency: str | None) -> str:
    """One canonical receipt body: greeting + item summary + paid/pickup line."""
    biz = (order.get("business_name")
           or getattr(config, "business_name", "") or "the restaurant")
    cur = (currency or order.get("currency") or "cad").upper()
    sym = "CA$" if cur == "CAD" else "$"
    if amount_cents is not None:
        total = amount_cents / 100
    else:
        total = order.get("total", 0) or 0
    first = (order.get("customer_name") or "").split(" ")[0]
    hi = f"Hi {first}! " if first else ""

    items = order.get("items", []) or []
    item_lines = []
    for it in items:
        qty = int(it.get("quantity", 1) or 1)
        size = f" ({it['size']})" if it.get("size") else ""
        item_lines.append(f"  {qty}x {it.get('name', 'item')}{size}")
    summary = "\n".join(item_lines) if item_lines else "  your order"

    if paid:
        head = f"{hi}Payment received ✓ Your order at {biz} is confirmed and paid."
        tail = "We'll have it ready shortly."
    else:
        head = f"{hi}Your order at {biz} is confirmed."
        tail = "We'll have it ready for pickup shortly."

    return f"{head}\n\n{summary}\n\nTotal: {sym}{total:.2f}\n\n{tail}"


async def send_order_receipt(
    order: dict[str, Any],
    config,
    *,
    order_id: str,
    paid: bool = True,
    amount_cents: int | None = None,
    currency: str | None = None,
) -> dict:
    """Send the customer their order receipt — ONCE, guarded.

    order_id is the idempotency key (the pos_order_id / checkout session id).
    `paid` picks the paid-receipt copy vs the pay-at-pickup confirmation copy.
    `amount_cents`/`currency` let the payment webhook pass the settled amount;
    otherwise the order's own total is used.
    """
    phone = (order.get("caller_phone") or "").strip()
    if not phone:
        return {"sent": False, "reason": "no_phone", "order_id": order_id}

    if not _killswitch_on():
        logger.info("order receipt suppressed by killswitch (order=%s)", order_id)
        return {"sent": False, "reason": "killswitch", "order_id": order_id}

    merchant_id = order.get("merchant_id") or getattr(config, "merchant_id", "") or ""
    optout = await fetch_optout_status(merchant_id, phone)
    if optout.get("transactional_optout"):
        logger.info("order receipt suppressed by transactional opt-out (order=%s)", order_id)
        return {"sent": False, "reason": "transactional_optout", "order_id": order_id}

    # Idempotency claim LAST, right before the send, so a suppressed receipt
    # (opt-out / killswitch) never burns the one-shot claim for the order.
    if not await _claim_receipt(order_id):
        return {"sent": False, "reason": "already_sent", "order_id": order_id}

    body = _format_receipt(order, config, paid=paid,
                           amount_cents=amount_cents, currency=currency)
    try:
        res = await send_sms(phone, body)
    except Exception as e:  # noqa: BLE001 — receipt never blocks the caller flow
        logger.error("order receipt SMS failed (order=%s): %s", order_id, e)
        return {"sent": False, "reason": "send_error", "order_id": order_id}

    sent = bool(res.get("sent"))
    logger.info("order receipt SMS order=%s paid=%s sent=%s", order_id, paid, sent)
    return {"sent": sent, "reason": None if sent else res.get("reason", "send_failed"),
            "order_id": order_id}
