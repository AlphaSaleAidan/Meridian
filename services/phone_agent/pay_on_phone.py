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

DELIVERY FAN-OUT (2026-07-16): the release path (pay_at_pickup, and the
post-payment release for pay_now) runs the POS push, the customer SMS and a
merchant notification SMS as PARALLEL legs with per-leg exception isolation —
never either/or — and records each leg's outcome on the phone_orders row
(pos_delivery_status / sms_delivery_status / merchant_notify_status /
delivery_detail) so support can see exactly what fired and what failed.
Per-merchant toggles: phone_agent_config.delivery_channels (JSONB).
"""
import asyncio
import logging
import os
from functools import partial
from typing import Any

import httpx

from delivery_channels import (
    DEFERRED,
    SKIPPED_DISABLED,
    SKIPPED_NO_NUMBER,
    base_order_row,
    create_pos_for_config,
    customer_sms_leg,
    delivery_columns,
    leg_outcome,
    merchant_sms_leg,
    pos_delivery_leg,
    pos_outcome,
    resolve_channels,
    run_legs,
    save_order_row,
)
from merchant_config import MerchantPhoneConfig
from order_receipt import ReceiptClaim, send_order_receipt
from payment_links import create_checkout
from sms_checkout import send_checkout_sms

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

# POS PUSH AFTER PAYMENT (product decision 2026-07-04): for virtually-paid
# orders (pay_now) the POS ticket is NOT created until payment confirms — the
# old "hold" was only a DB flag while the open ticket already sat in the
# merchant's POS, so unpaid orders could still be cooked. With this on, the
# ticket is pushed by mark_order_paid() when Stripe confirms. Set 0 to restore
# the old create-up-front behavior.
POS_PUSH_AFTER_PAYMENT = os.getenv("POS_PUSH_AFTER_PAYMENT", "1") == "1"


async def _create_pos(order: dict, config: MerchantPhoneConfig) -> dict:
    """Create the POS order with the merchant's creds (env fallback for the
    Square demo). Honors the per-merchant demo_safe guard."""
    return await create_pos_for_config(order, config)


def is_demo(merchant_id: str) -> bool:
    """Demo/synthetic merchant → simulate payment, never charge."""
    return merchant_id == DEMO_MERCHANT_ID


def resolve_mode(config: MerchantPhoneConfig, pay_choice: str = "") -> str:
    """Resolve the effective payment path for this order.

    CASH: when the merchant enabled accept_cash AND the caller chose cash, the
    order takes the 'cash' path (unpaid, released to the kitchen now, NO payment
    link) regardless of the configured payment_mode. This gate is fail-safe: an
    'cash' choice with accept_cash OFF is ignored and falls through to the
    merchant's real mode, so a merchant that never opted in can never end up
    dispatching an unpaid cash order.

    `optional` defers to the caller's pay_choice (defaults to pay_now if
    unset/invalid)."""
    choice = (pay_choice or "").strip().lower()
    if choice == "cash" and getattr(config, "accept_cash", False):
        return "cash"
    mode = getattr(config, "payment_mode", "pay_now")
    if mode == "optional":
        return choice if choice in ("pay_now", "pay_at_pickup") else "pay_now"
    return mode if mode in ("pay_now", "pay_at_pickup") else "pay_now"


async def dispatch_order(
    order: dict[str, Any],
    config: MerchantPhoneConfig,
    caller_info: dict,
    pos_result: dict | None = None,
    pay_choice: str = "",
) -> dict:
    """Order dispatch shared by the live bot, the Vapi route, and the tests.
    Owns POS creation so its timing follows the payment mode:

      pay_now       → POS push DEFERRED until payment confirms (mark_order_paid
                      creates the ticket) — an unpaid order never reaches the
                      kitchen. Pay link + SMS go out now; the merchant
                      notification is deferred with the ticket.
      pay_at_pickup → POS push, customer SMS and merchant notification SMS run
                      NOW as parallel legs (per-leg exception isolation).

    `pos_result` may be passed by legacy callers that already created the POS
    order; when it carries a real pos_order_id it is honored (too late to defer).

    Returns {"mode", "released", "pos_result", "sms_sent", "payment_link",
    "delivery" (per-leg outcomes), "phone_order_id", ...}.
    """
    mode = resolve_mode(config, pay_choice)
    channels = resolve_channels(config)
    if mode == "cash":
        # PAY WITH CASH: unpaid, released to the kitchen NOW (mirrors
        # pay_at_pickup), flagged CASH ON PICKUP, and NO payment link created.
        return await _cash_release(order, config, caller_info, pos_result, channels)
    if mode == "pay_now":
        already_created = bool((pos_result or {}).get("pos_order_id"))
        if POS_PUSH_AFTER_PAYMENT and not already_created:
            # Placeholder — the real ticket is pushed by mark_order_paid() on payment.
            pos_result = {"success": False, "method": "deferred",
                          "pos_order_id": "", "deferred": True}
        elif pos_result is None:
            pos_result = await _create_pos(order, config)
        result = await collect_pay_now(order, config, caller_info, pos_result, channels)
        result["mode"] = "pay_now"
        result["released"] = False  # held until paid
        result["pos_deferred"] = bool(pos_result.get("deferred"))
        result["pos_result"] = pos_result
        return result
    # pay_at_pickup — release to kitchen now, all legs in parallel.
    return await _fanout_release(order, config, caller_info, pos_result, channels)


async def _fanout_release(
    order: dict[str, Any],
    config: MerchantPhoneConfig,
    caller_info: dict,
    pos_result: dict | None,
    channels: dict[str, bool],
) -> dict:
    """pay_at_pickup: fire every enabled delivery leg NOW, concurrently.

    ORDERING EXCEPTION (P1 fix, post-#332): when the POS channel is enabled the
    customer_sms leg is chained AFTER the pos leg so the checkout link carries
    the REAL pos_order_id (Stripe client_reference_id + metadata) and the
    payment webhook matches the exact row — not merchant+phone-latest, which
    can mark the WRONG order paid for a repeat caller with two open orders.
    If the pos leg fails, the SMS still goes out with "" (degraded matching,
    same as pre-fix). merchant_sms stays fully parallel.

    A POS failure never suppresses the SMS legs (and vice versa); each leg's
    outcome lands in the phone_orders per-channel columns.
    """
    order.setdefault("caller_phone", caller_info.get("phone") or order.get("caller_phone", ""))

    legs = {}
    outcomes: dict[str, dict] = {}
    pos_enabled = channels.get("pos", True) or pos_result is not None
    sms_enabled = channels.get("customer_sms", True)

    pos_task: asyncio.Task | None = None
    if pos_enabled and sms_enabled:
        # Shared task: run_legs awaits it as the pos leg, and the customer_sms
        # leg awaits the SAME task to pick up the real pos_order_id first.
        pos_task = asyncio.create_task(pos_delivery_leg(order, config, pos_result))
        legs["pos"] = lambda: pos_task
    elif pos_enabled:
        legs["pos"] = partial(pos_delivery_leg, order, config, pos_result)
    else:
        outcomes["pos"] = leg_outcome(SKIPPED_DISABLED)

    if not sms_enabled:
        outcomes["customer_sms"] = leg_outcome(SKIPPED_DISABLED)
    elif pos_task is not None:
        async def _sms_after_pos() -> dict:
            try:
                pos_out = await pos_task
                pos_id = str((pos_out.get("pos_result") or {}).get("pos_order_id") or "")
            except BaseException:  # noqa: BLE001 — a pos blow-up never strands the SMS
                pos_id = ""
            return await customer_sms_leg(order, config, pos_order_id=pos_id)
        legs["customer_sms"] = _sms_after_pos
    else:
        # POS disabled / not configured: SMS goes out immediately, unmatched
        # checkout ("") exactly as before.
        legs["customer_sms"] = partial(customer_sms_leg, order, config)

    if channels.get("merchant_sms", True):
        legs["merchant_sms"] = partial(merchant_sms_leg, order, config)
    else:
        outcomes["merchant_sms"] = leg_outcome(SKIPPED_DISABLED)

    outcomes.update(await run_legs(legs))

    final_pos = (outcomes.get("pos") or {}).get("pos_result") or pos_result \
        or {"success": False, "reason": "channel_disabled", "pos_order_id": ""}
    sms_out = outcomes.get("customer_sms") or {}
    payment_link = sms_out.get("payment_link", "")

    row = {
        **base_order_row(order, final_pos),
        # kitchen released now (legacy pay_at_pickup semantics)
        "status": "placed",
        "kitchen_released": True,
        "sms_sent": sms_out.get("status") == "sent",
        **delivery_columns(outcomes),
    }
    if payment_link:
        row["payment_link"] = payment_link
        row["payment_method"] = sms_out.get("method", "")
        row["payment_status"] = "pending"
    phone_order_id = await save_order_row(row)

    # RECEIPT RECONCILIATION: the pay_at_pickup order is released to the kitchen
    # now and has NO downstream payment webhook to text the caller a receipt (the
    # customer_sms leg above is the pay-LINK; for pay_at_pickup there is no link).
    # Fire the shared, idempotent order-receipt SMS so the streaming path matches
    # the turn-based path. CLAIM on the phone_orders row we just inserted — its
    # primary key (phone_order_id) is ALWAYS present, whereas pos_order_id is ""
    # when POS is disabled/failed (the old pos_order_id claim matched nothing and
    # silently dropped the receipt). Best-effort — a receipt hiccup never strands
    # the released order.
    real_pos_id = str((final_pos or {}).get("pos_order_id") or "")
    if phone_order_id:
        receipt_claim = ReceiptClaim(column="id", value=str(phone_order_id),
                                     dedup_id=real_pos_id or str(phone_order_id))
    elif real_pos_id:
        receipt_claim = ReceiptClaim(column="pos_order_id", value=real_pos_id,
                                     dedup_id=real_pos_id)
    else:
        # No Supabase (tests/demo): no row id and no pos id — dedup on merchant+phone.
        receipt_claim = ReceiptClaim(
            merchant_id=config.merchant_id,
            caller_phone=order.get("caller_phone", ""),
            dedup_id=f"{config.merchant_id}:{order.get('caller_phone', '')}",
        )
    try:
        await send_order_receipt(
            order, config,
            order_id=real_pos_id or (str(phone_order_id) if phone_order_id else "pay_at_pickup"),
            claim=receipt_claim,
            paid=False,
        )
    except Exception as e:  # noqa: BLE001 — receipt never blocks a released order
        logger.error("pay_at_pickup receipt SMS failed: %s", e)

    logger.info(
        "Order fan-out (pay_at_pickup): merchant=%s pos=%s customer_sms=%s merchant_sms=%s",
        config.merchant_id,
        (outcomes.get("pos") or {}).get("status"),
        (outcomes.get("customer_sms") or {}).get("status"),
        (outcomes.get("merchant_sms") or {}).get("status"),
    )

    return {
        "mode": "pay_at_pickup",
        "released": True,
        "sms_sent": sms_out.get("status") == "sent",
        "payment_link": payment_link,
        "pos_result": final_pos,
        "delivery": outcomes,
        "phone_order_id": phone_order_id,
    }


async def _cash_release(
    order: dict[str, Any],
    config: MerchantPhoneConfig,
    caller_info: dict,
    pos_result: dict | None,
    channels: dict[str, bool],
) -> dict:
    """PAY WITH CASH release: the order is created and released to the kitchen
    NOW (like pay_at_pickup) but flagged CASH ON PICKUP / UNPAID, and NO payment
    link / checkout SMS is ever generated.

    Legs (parallel, per-leg exception isolation):
      pos          → ticket pushed into the merchant's POS now (marked cash so
                     build_kitchen_note prints "CASH ON PICKUP").
      merchant_sms → staff notification so the kitchen sees the order + that it's
                     collect-cash-on-pickup.
    There is deliberately NO customer_sms leg — a cash order never gets a pay
    link (create_checkout / send_checkout_sms are never called on this path).
    """
    order.setdefault("caller_phone", caller_info.get("phone") or order.get("caller_phone", ""))
    # Flag the order as cash so the POS kitchen ticket shows CASH ON PICKUP.
    order["payment_method"] = "cash"

    legs: dict = {}
    outcomes: dict[str, dict] = {}
    if channels.get("pos", True) or pos_result is not None:
        legs["pos"] = partial(pos_delivery_leg, order, config, pos_result)
    else:
        outcomes["pos"] = leg_outcome(SKIPPED_DISABLED)

    # Cash orders carry NO pay link — the customer_sms leg is skipped entirely.
    outcomes["customer_sms"] = leg_outcome("skipped_cash")

    if channels.get("merchant_sms", True):
        legs["merchant_sms"] = partial(
            merchant_sms_leg, order, config, body=_cash_merchant_body(order, config))
    else:
        outcomes["merchant_sms"] = leg_outcome(SKIPPED_DISABLED)

    outcomes.update(await run_legs(legs))

    final_pos = (outcomes.get("pos") or {}).get("pos_result") or pos_result \
        or {"success": False, "reason": "channel_disabled", "pos_order_id": ""}

    row = {
        **base_order_row(order, final_pos),
        "status": "placed",
        "kitchen_released": True,
        "payment_method": "cash",
        "payment_status": "unpaid",
        "sms_sent": False,
        **delivery_columns(outcomes),
    }
    phone_order_id = await save_order_row(row)

    logger.info(
        "Order fan-out (cash on pickup): merchant=%s pos=%s merchant_sms=%s (no pay link)",
        config.merchant_id,
        (outcomes.get("pos") or {}).get("status"),
        (outcomes.get("merchant_sms") or {}).get("status"),
    )

    return {
        "mode": "cash",
        "released": True,
        "sms_sent": False,
        "payment_link": "",
        "pos_result": final_pos,
        "delivery": outcomes,
        "phone_order_id": phone_order_id,
    }


def _cash_merchant_body(order: dict, config: MerchantPhoneConfig) -> str:
    """Staff notification body for a cash order — makes the UNPAID / collect-cash
    status unmissable at the top of the ticket text."""
    from order_router import _format_order_summary
    summary = _format_order_summary(
        {**order, "business_name": getattr(config, "business_name", "") or ""})
    return "💵 CASH ON PICKUP — collect payment at the counter.\n" + summary


async def collect_pay_now(
    order: dict[str, Any],
    config: MerchantPhoneConfig,
    caller_info: dict,
    pos_result: dict,
    channels: dict[str, bool] | None = None,
) -> dict:
    """
    Pay-now path: create the Square payment link (POS ticket deferred), text it
    to the caller, and write the phone_orders row as `awaiting_payment` with
    `payment_status='pending'` — the kitchen ticket is HELD until paid.

    The pay-link SMS is payment-critical and always attempts regardless of the
    customer_sms channel toggle (disabling it would strand pay_now orders).
    The merchant notification is deferred alongside the ticket and sent by
    mark_order_paid() on release.

    Returns {"payment_link", "sms_sent", "method", "simulated_paid", ...}.
    """
    channels = channels or resolve_channels(config)
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

    # Per-channel outcomes for the held order.
    if pos_result.get("deferred"):
        pos_leg = leg_outcome(DEFERRED, pos_result=pos_result)
    else:
        pos_leg = pos_outcome(pos_result, already_created=True)
    if not payment_result.get("url"):
        sms_leg = leg_outcome("skipped_no_link",
                              method=payment_result.get("method", "none"))
    elif sms_result.get("sent"):
        sms_leg = leg_outcome("sent", payment_link=payment_result["url"],
                              method=payment_result.get("method", ""))
    else:
        sms_leg = leg_outcome("failed",
                              error=str(sms_result.get("reason", "sms_failed")),
                              payment_link=payment_result.get("url", ""),
                              method=payment_result.get("method", ""))
    if not channels.get("merchant_sms", True):
        merchant_leg = leg_outcome(SKIPPED_DISABLED)
    elif not (getattr(config, "transfer_number", "") or "").strip():
        merchant_leg = leg_outcome(SKIPPED_NO_NUMBER)
    else:
        # Held with the ticket — released (sent) by mark_order_paid.
        merchant_leg = leg_outcome(DEFERRED)
    outcomes = {"pos": pos_leg, "customer_sms": sms_leg, "merchant_sms": merchant_leg}

    # Write the held order: pending payment, ticket NOT released to the kitchen.
    phone_order_id = await _save_held_order(
        order, pos_result, payment_result, sms_result, outcomes,
    )

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
        "delivery": outcomes,
        "phone_order_id": phone_order_id,
    }


async def _save_held_order(
    order: dict, pos_result: dict, payment_result: dict, sms_result: dict,
    outcomes: dict[str, dict] | None = None,
) -> str | None:
    """Insert the phone_orders row in the HELD state (anti-scam): the order is
    created but `status='awaiting_payment'` and `kitchen_released=false`, so the
    kitchen ticket / staff SMS is NOT sent until payment confirms."""
    row = {
        **base_order_row(order, pos_result),
        # anti-scam: held until paid
        "status": "awaiting_payment",
        "kitchen_released": False,
        "payment_status": "pending",
        "payment_link": payment_result.get("url", ""),
        "payment_method": payment_result.get("method", ""),
        "sms_sent": sms_result.get("sent", False),
    }
    if outcomes:
        row.update(delivery_columns(outcomes))
    return await save_order_row(row)


async def mark_order_paid(
    merchant_id: str,
    caller_phone: str = "",
    pos_order_id: str = "",
    simulate: bool = False,
    method: str = "",
    card_brand: str = "",
    card_last4: str = "",
    payment_txn_id: str = "",
    paid_amount_cents: int = 0,
) -> dict:
    """Payment confirmed → flip the held order to paid AND release the kitchen
    ticket. Matches by pos_order_id when known (most precise); else by
    merchant+phone among the caller's OPEN (not-yet-paid) orders, disambiguated
    by the amount actually paid so a repeat caller with two open orders pays the
    RIGHT one (previously it blindly took the latest, so paying the $30 order
    could release + settle the $12 one). Idempotent.

    Release now fans out too: the deferred POS ticket is pushed AND the
    merchant notification SMS goes to the merchant's line, each recorded on the
    row's per-channel columns.

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
        # SELECT the held row first: (a) PATCH by primary key — the phone-match
        # query's order/limit params are ignored by PostgREST on PATCH and would
        # hit every row for that caller; (b) we need the stored order to push the
        # deferred POS ticket now that payment is confirmed.
        row = await _fetch_held_order(f"?pos_order_id=eq.{pos_order_id}")
        matched_by = "pos_order_id"
    elif merchant_id and caller_phone:
        row, matched_by = await _match_open_order_by_phone(
            merchant_id, caller_phone, paid_amount_cents)
    else:
        logger.warning("mark_order_paid: no key to match an order")
        return {"released": False, "matched_by": "none"}

    if row is None:
        logger.warning("mark_order_paid: no order matched (%s)", matched_by)
        return {"released": False, "matched_by": matched_by}

    # BILLING RECONCILIATION — the last line of defense on REAL money: if the
    # customer paid LESS than the total this order was confirmed at (a
    # line-item builder drifting from the order total again), the order still
    # releases (the shortfall is our bug, not the customer's), but it must
    # never pass silently: CRITICAL log + best-effort ops email. Overpayment
    # (customer surcharge riding on top) is expected and not flagged.
    _reconcile_paid_amount(row, paid_amount_cents, merchant_id)

    # CLAIM FIRST (compare-and-swap): flip to paid ONLY if not already paid.
    # This is the idempotency gate — the release fan-out below (POS push +
    # merchant SMS) runs ONLY for the event that wins the claim, so a duplicate
    # delivery (Square payment.created + payment.updated, Stripe retries) on
    # another worker can't double-push the kitchen ticket or double-text the
    # merchant. (Previously the POS push ran BEFORE the flip, so both events
    # pushed.) The claim carries the paid/kitchen flags + payment-method columns.
    claim_patch = {
        "payment_status": "paid",
        "status": "paid",
        "kitchen_released": True,
    }
    if method:
        claim_patch["payment_method"] = method
    if card_brand:
        claim_patch["card_brand"] = card_brand
    if card_last4:
        claim_patch["card_last4"] = card_last4
    if payment_txn_id:
        claim_patch["payment_txn_id"] = payment_txn_id
    if simulate:
        claim_patch["payment_note"] = "simulated (demo)"

    try:
        claimed = await _claim_order_paid(row.get("id"), claim_patch)
    except Exception as e:  # noqa: BLE001
        logger.error("mark_order_paid claim failed: %s", e)
        return {"released": False, "matched_by": matched_by}
    if not claimed:
        # Another worker / a duplicate event already paid + released this order.
        logger.info("mark_order_paid: order %s already paid — duplicate event ignored (%s)",
                    row.get("id"), matched_by)
        return {"released": False, "matched_by": matched_by, "duplicate": True}

    # ── We WON the claim: run the release fan-out exactly once. ──
    # What still needs to fire now that payment confirmed?
    #  - deferred POS ticket (no pos_order_id yet)
    #  - merchant notification SMS — only for a HELD row (pay_now deferral;
    #    pay_at_pickup rows already notified at order time).
    needs_pos_push = POS_PUSH_AFTER_PAYMENT and not (row.get("pos_order_id") or "")
    row_was_held = not row.get("kitchen_released")
    notify_deferred = row_was_held and (
        (row.get("merchant_notify_status") or DEFERRED) == DEFERRED
    )

    cfg = None
    if needs_pos_push or notify_deferred:
        try:
            from merchant_config import get_merchant_config
            cfg = await get_merchant_config(merchant_id or row.get("merchant_id", ""))
        except Exception as e:  # noqa: BLE001 — release must survive a config hiccup
            logger.error("mark_order_paid: config load failed: %s", e)

    order = {k: row.get(k) for k in (
        "merchant_id", "customer_name", "order_type", "items",
        "subtotal", "tax", "total", "delivery_address",
        "special_requests", "caller_phone",
    )}
    # The pos ids + fan-out telemetry go in a SEPARATE best-effort PATCH: the
    # paid flag is already committed by the claim, so a missing/renamed column
    # here (or a POS/SMS hiccup) must never un-commit the money truth.
    post_patch: dict[str, Any] = {}
    detail = dict(row.get("delivery_detail") or {})

    # POS PUSH AFTER PAYMENT: the ticket was deferred at order time — payment
    # is now confirmed, so push it to the kitchen. (simulate/demo included: the
    # immediate simulated "paid" plays the same release path, and demo_safe
    # merchants are logs-only in the connector.)
    pos_pushed = False
    if needs_pos_push and cfg is not None:
        try:
            pos_result = await _create_pos(order, cfg)
            post_patch["pos_order_id"] = pos_result.get("pos_order_id", "")
            post_patch["pos_success"] = bool(pos_result.get("success"))
            if pos_result.get("kitchen_fired"):
                # Clover print_event accepted on the deferred push.
                post_patch["fulfillment_state"] = "kitchen_fired"
            pos_pushed = bool(pos_result.get("success"))
            released_pos = pos_outcome(pos_result)
            released_pos["released_at_payment"] = True
            post_patch["pos_delivery_status"] = released_pos["status"]
            detail["pos"] = released_pos
        except Exception as e:  # noqa: BLE001 — never lose the paid flag over a POS hiccup
            logger.error("deferred POS push failed (order stays SMS/email ticket): %s", e)
            post_patch["pos_delivery_status"] = "failed"
            detail["pos"] = leg_outcome("failed", error=str(e), released_at_payment=True)

    # MERCHANT NOTIFICATION RELEASE: the staff SMS was held with the ticket —
    # send it now so a merchant WITHOUT a connected POS still gets the order.
    if cfg is not None and notify_deferred:
        try:
            if resolve_channels(cfg).get("merchant_sms", True):
                from order_router import _format_order_summary
                summary = "✅ PAID — make this order now.\n" + _format_order_summary(
                    {**order, "business_name": getattr(cfg, "business_name", "") or ""}
                )
                notify = await merchant_sms_leg(order, cfg, body=summary)
            else:
                notify = leg_outcome(SKIPPED_DISABLED)
            notify["released_at_payment"] = True
            post_patch["merchant_notify_status"] = notify["status"]
            detail["merchant_sms"] = notify
        except Exception as e:  # noqa: BLE001 — notification failure never blocks the paid flag
            logger.error("merchant release SMS failed: %s", e)
            post_patch["merchant_notify_status"] = "failed"
            detail["merchant_sms"] = leg_outcome("failed", error=str(e),
                                                 released_at_payment=True)

    # POST-CLAIM PATCH (best-effort): pos ids + fan-out telemetry. Logged, never
    # raised — the paid flag/kitchen release already committed in the claim.
    if post_patch:
        post_patch["delivery_detail"] = detail
        try:
            await _patch_order_row(row.get("id"), post_patch)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "mark_order_paid: post-claim update failed (paid flag already committed): %s", e,
            )

    logger.info("Order paid + kitchen released (matched_by=%s pos_pushed=%s notify=%s)",
                matched_by, pos_pushed, post_patch.get("merchant_notify_status", "n/a"))
    return {"released": True, "matched_by": matched_by, "pos_pushed": pos_pushed}


async def _patch_order_row(row_id: str | None, patch: dict) -> None:
    """PATCH a phone_orders row by primary key. Raises on transport errors or a
    non-2xx PostgREST response so callers can decide criticality."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/phone_orders?id=eq.{row_id}",
            json=patch,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            timeout=10,
        )
        if resp.status_code >= 300:
            raise RuntimeError(
                f"phone_orders PATCH {resp.status_code}: {resp.text[:200]}"
            )


async def _claim_order_paid(row_id: str | None, patch: dict) -> list[dict]:
    """Compare-and-swap flip of an order to paid: PATCH ... WHERE id=? AND
    status<>'paid', asking for the updated rows back. Returns the matched rows
    ([] when another worker / a duplicate event already paid it).

    This is THE idempotency gate for the release fan-out. Under multiple uvicorn
    workers, one payment can arrive as two events (Square emits payment.created
    AND payment.updated; Stripe retries on any non-2xx), so the naive
    SELECT-then-PATCH-by-id let both events pass the unpaid check and each pushed
    a second kitchen ticket + texted the merchant again. The status guard makes
    exactly one event win. Mirrors website_order_dispatch.mark_paid_and_dispatch."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/phone_orders?id=eq.{row_id}&status=neq.paid",
            json=patch,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            timeout=10,
        )
        if resp.status_code >= 300:
            raise RuntimeError(
                f"phone_orders claim PATCH {resp.status_code}: {resp.text[:200]}"
            )
        try:
            return resp.json() or []
        except Exception:  # noqa: BLE001 — empty/no body ⇒ no row matched
            return []


def _order_base_cents(row: dict) -> int:
    """A phone_orders row's base order total in cents (total is stored in the
    market currency's major units). 0 when unparseable."""
    try:
        return int(round(float(row.get("total") or 0) * 100))
    except (TypeError, ValueError):
        return 0


def _reconcile_paid_amount(row: dict, paid_amount_cents: int,
                           merchant_id: str) -> None:
    """CRITICAL-log (+ best-effort ops email) when a payment settles below the
    order's confirmed total. Never raises, never blocks the release."""
    try:
        expected = _order_base_cents(row)
        if not (paid_amount_cents and expected):
            return  # amount unknown (simulate, non-Stripe rails) — nothing to say
        if paid_amount_cents >= expected:
            return
        detail = (
            f"phone order {row.get('pos_order_id') or row.get('id')} for merchant "
            f"{merchant_id or row.get('merchant_id')} settled at {paid_amount_cents}¢ "
            f"but was confirmed at {expected}¢ — a payment-link builder is billing "
            f"below the order total (tax/modifier drift). Merchant is being "
            f"shorted; fix the builder before more orders pay. "
            f"RUN: docs/runbooks/incidents/pay-mismatch.md (SEV-1).")
        logger.critical("UNDERPAYMENT DETECTED: %s", detail)

        async def _alert():
            try:
                from src.email.send import send_anomaly_alert
                await send_anomaly_alert(
                    os.getenv("MERIDIAN_OPS_ALERT_EMAIL",
                              "aidanpierce72@gmail.com"),
                    row.get("business_name") or merchant_id or "Meridian",
                    "Phone order underpayment — billing drift",
                    detail, severity="high")
            except Exception as e:  # noqa: BLE001 — alerting never breaks payment
                logger.error("underpayment alert email failed: %s", e)
            # DEFCON 1 — a live order settled short: page every responder.
            try:
                from src.services.defcon_alert import notify_defcon
                await notify_defcon(
                    1, "Live phone order settled below confirmed total",
                    detail, protocol="pay-mismatch.md", event_key="underpayment")
            except Exception as e:  # noqa: BLE001
                logger.error("underpayment DEFCON page failed: %s", e)

        import asyncio
        asyncio.ensure_future(_alert())
    except Exception as e:  # noqa: BLE001 — reconciliation never breaks payment
        logger.error("paid-amount reconciliation failed: %s", e)


async def _match_open_order_by_phone(
    merchant_id: str, caller_phone: str, paid_amount_cents: int,
) -> tuple[dict | None, str]:
    """Pick the caller's order this payment belongs to when no pos_order_id ties
    it down (the normal deferred pay_now case).

    Fetches the caller's recent orders, drops ones already finalized (paid /
    refunded / disputed) so a settled order is never re-matched, then — when the
    paid amount is known and more than one order is still open — chooses the one
    whose base total is CLOSEST to what was paid (robust to the small per-order
    surcharge that rides the Stripe charge). Falls back to most-recent when there
    is a single candidate or no amount to disambiguate.

    Returns (row_or_None, matched_by)."""
    rows = await _fetch_orders(
        f"?merchant_id=eq.{merchant_id}&caller_phone=eq.{caller_phone}"
        f"&order=created_at.desc&limit=10"
    )
    if not rows:
        return None, "merchant_phone"

    _final = {"paid", "refunded", "disputed"}
    candidates = [
        r for r in rows
        if (r.get("payment_status") or "") != "paid"
        and (r.get("status") or "") not in _final
    ] or rows  # if everything looks finalized, fall back to the raw list

    if paid_amount_cents and len(candidates) > 1:
        best = min(candidates, key=lambda r: abs(_order_base_cents(r) - paid_amount_cents))
        logger.info(
            "mark_order_paid: %d open orders for %s/%s — matched by amount "
            "(paid=%d¢, order total=%d¢)",
            len(candidates), merchant_id, caller_phone,
            paid_amount_cents, _order_base_cents(best),
        )
        return best, "merchant_phone_amount"

    if len(candidates) > 1:
        logger.warning(
            "mark_order_paid: %d open orders for %s/%s and no paid amount to "
            "disambiguate — using most recent (may be wrong)",
            len(candidates), merchant_id, caller_phone,
        )
    return candidates[0], "merchant_phone"


async def _fetch_orders(query: str) -> list[dict]:
    """Fetch all order rows matched by `query` (select honors order/limit)."""
    sep = "&" if "?" in query else "?"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/phone_orders{query}{sep}select=*",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10,
            )
            return resp.json() if resp.status_code == 200 else []
    except Exception as e:  # noqa: BLE001
        logger.error("_fetch_orders failed: %s", e)
        return []


async def _fetch_held_order(query: str) -> dict | None:
    """Fetch the single order row matched by `query` (select honors order/limit)."""
    sep = "&" if "?" in query else "?"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/phone_orders{query}{sep}select=*",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10,
            )
            rows = resp.json() if resp.status_code == 200 else []
            return rows[0] if rows else None
    except Exception as e:  # noqa: BLE001
        logger.error("_fetch_held_order failed: %s", e)
        return None
