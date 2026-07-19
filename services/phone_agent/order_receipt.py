"""
Shared customer order-receipt SMS — ONE code path for every phone order.

Both the turn-based Vapi path and the streaming Pipecat path complete orders and
owe the caller the same confirmation receipt ("your order is confirmed"). Before
this module the receipt was duplicated across the Stripe / Clover / pay-redirect
payment webhooks (pay_now only) and never fired at all for pay_at_pickup orders
or for streaming orders released without a payment webhook. This helper is the
single sender they all call.

Guarantees:
  * IDEMPOTENT on the row, not on an opaque "order id". Different flows key the
    phone_orders row differently and the payment-time pos_order_id is NOT always
    on the row:
      - pay_now-Stripe: the POS ticket is deferred, so the held row carries
        pos_order_id="" at checkout time; the webhook only has the Stripe
        SESSION id. Claiming on pos_order_id there matched ZERO rows and SILENTLY
        DROPPED the receipt. Claim on (merchant_id, caller_phone)-most-recent —
        the exact row mark_order_paid just released.
      - streaming / POS-failed pay_at_pickup: pos_order_id="" on the row, but the
        insert returned the row's primary key (phone_order_id). Claim on id.
      - Clover-native: a real pos_order_id is on the row. Claim on pos_order_id.
    So callers pass a ReceiptClaim describing WHICH column the value lives in
    (see send_order_receipt). The durable guard is a conditional PATCH on
    phone_orders.receipt_sent (see _claim_receipt): the first caller to flip
    false→true owns the send; every later caller (sidecar AND webhook both
    reporting the same order) reads the row as already claimed and sends nothing.
    When Supabase is unconfigured (tests / demo box) an in-process set stands in
    so a single process still never double-sends.
  * Respects the transactional opt-out (casl_compliance.fetch_optout_status) —
    a STOP that set transactional_optout kills the receipt.
  * Respects the killswitch env PHONE_RECEIPT_SMS_ENABLED (default on) so the
    receipt can be cut fleet-wide without a deploy.

Cross-process note: the Stripe receipt fires in the API process while the
streaming receipt fires in the Pipecat sidecar, so the in-process _sent_ids set
is NOT a cross-process guard — the DB conditional PATCH (migration 070) is the
only real cross-process/cross-worker de-dupe. Until 070 is applied, or if
Supabase is unconfigured, the in-proc set only protects a single process:
recommend workers=1 in that window. Once 070 is applied the row-aware claim
covers every worker/process.

Result: {"sent": bool, "reason"?: str, "order_id": str}.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

from casl_compliance import fetch_optout_status
from sms_checkout import send_sms

logger = logging.getLogger("meridian.phone_agent.order_receipt")

# PostgREST columns a receipt claim may key on. Whitelisted so a claim value can
# never inject a filter — the column is chosen by the call site, not the caller.
_CLAIMABLE_COLUMNS = ("id", "pos_order_id")


@dataclass(frozen=True)
class ReceiptClaim:
    """Which phone_orders row this receipt belongs to, and how to find it.

    Exactly one strategy is used, tried in this order:
      1. column/value  — an exact-match column the row RELIABLY carries:
         'id' (the phone_order_id returned at insert) or 'pos_order_id'
         (a real POS ticket id). This is the precise, single-row claim.
      2. merchant_id/caller_phone — most-recent row for that caller, used by the
         pay_now-Stripe webhook where neither the row id nor a real pos_order_id
         is in hand but mark_order_paid just released the caller's newest order.

    `dedup_id` is the in-process backstop key (used only when Supabase is
    unconfigured, e.g. tests/demo) so a single process never double-sends.
    """
    column: str | None = None
    value: str = ""
    merchant_id: str = ""
    caller_phone: str = ""
    dedup_id: str = ""

    @property
    def has_target(self) -> bool:
        return bool((self.column and self.value)
                    or (self.merchant_id and self.caller_phone))

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


def _in_proc_claim(dedup_id: str) -> bool:
    """Same-process backstop: first sighting of dedup_id wins, later ones skip.
    Only used when Supabase is unconfigured OR the durable claim can't run. This
    is NOT cross-process (Stripe receipts run in the API proc, streaming in the
    sidecar) — the DB claim below is the real cross-process guard."""
    if not dedup_id:
        # No key at all: fail closed (skip) so we never spam an unbounded loop.
        return False
    if dedup_id in _sent_ids:
        return False
    _sent_ids.add(dedup_id)
    return True


async def _claim_target_row_id(claim: ReceiptClaim) -> str | None:
    """Resolve the phone_orders primary key for a merchant+phone most-recent
    claim. PATCH ignores order/limit, so (as mark_order_paid does) we SELECT the
    newest matching row's id and then claim by id. Returns None if no row."""
    url = (
        f"{SUPABASE_URL}/rest/v1/phone_orders"
        f"?merchant_id=eq.{claim.merchant_id}"
        f"&caller_phone=eq.{claim.caller_phone}"
        f"&order=created_at.desc&limit=1&select=id"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=10,
        )
    if resp.status_code >= 300:
        raise RuntimeError(f"claim-row lookup {resp.status_code}: {resp.text[:200]}")
    rows = resp.json() if resp.content else []
    return rows[0].get("id") if rows else None


async def _claim_receipt(claim: ReceiptClaim) -> bool:
    """Durable, cross-worker idempotency claim.

    Conditionally flip phone_orders.receipt_sent false→true on the ONE row this
    receipt belongs to (resolved from `claim`) and return whether THIS caller won
    the race (i.e. is responsible for sending). The filter receipt_sent=is.false
    makes the flip atomic at the row level (no TOCTOU); PostgREST returns the
    updated rows with Prefer: return=representation — a non-empty list means we
    flipped it (we send), an empty list means another caller already claimed it
    (we skip) OR no such row exists.

    When Supabase is unconfigured, fall back to the in-process set so a single
    process still never double-sends.
    """
    if not claim.has_target:
        return False
    if not SUPABASE_URL or not SUPABASE_KEY:
        return _in_proc_claim(claim.dedup_id)
    try:
        # Resolve to an exact (column, value) filter. A merchant+phone claim
        # first resolves the newest row's id (PATCH can't honor order/limit).
        if claim.column in _CLAIMABLE_COLUMNS and claim.value:
            column, value = claim.column, claim.value
        else:
            row_id = await _claim_target_row_id(claim)
            if not row_id:
                logger.warning(
                    "receipt claim: no phone_orders row for merchant=%s phone=%s — "
                    "degrading to in-proc guard", claim.merchant_id, claim.caller_phone,
                )
                return _in_proc_claim(claim.dedup_id)
            column, value = "id", row_id

        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/phone_orders"
                f"?{column}=eq.{value}&receipt_sent=is.false",
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
            return _in_proc_claim(claim.dedup_id)
        rows = resp.json() if resp.content else []
        return bool(rows)
    except Exception as e:  # noqa: BLE001 — never strand the receipt on a claim hiccup
        logger.warning("receipt claim failed (%s) — degrading to in-proc guard", e)
        return _in_proc_claim(claim.dedup_id)


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
    claim: ReceiptClaim | None = None,
    paid: bool = True,
    amount_cents: int | None = None,
    currency: str | None = None,
) -> dict:
    """Send the customer their order receipt — ONCE, guarded.

    order_id is the human/log id AND the in-process dedup backstop key.
    `claim` is the DURABLE, cross-process idempotency target — WHICH phone_orders
    row to flip receipt_sent on, and how to find it (see ReceiptClaim). When
    omitted it defaults to keying on pos_order_id=order_id (legacy behavior),
    which only matches when the row actually carries that pos_order_id; every
    real call site now passes an explicit claim so the row is always found.
    `paid` picks the paid-receipt copy vs the pay-at-pickup confirmation copy.
    `amount_cents`/`currency` let the payment webhook pass the settled amount;
    otherwise the order's own total is used.
    """
    if claim is None:
        claim = ReceiptClaim(column="pos_order_id", value=order_id, dedup_id=order_id)
    elif not claim.dedup_id:
        # Ensure the in-proc backstop always has a stable key.
        from dataclasses import replace
        claim = replace(claim, dedup_id=order_id)
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
    if not await _claim_receipt(claim):
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
