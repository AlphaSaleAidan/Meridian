"""
Voice → SMS payment-link handoff helper.

After the voice agent's submit_order tool fires, this helper:
  1. Normalises the order (matches the SMS path).
  2. Creates the POS order (falls through to logs-only if no token).
  3. Generates a payment link (Square-hosted when token is wired,
     Meridian-hosted fallback page otherwise).
  4. Logs to phone_orders.
  5. Sends the payment link SMS to the caller — BUT respects the
     marketing/transactional opt-out split: a STOP from the caller
     during the call kills marketing only, the payment link is
     transactional and still goes out unless transactional_optout is
     set.

DRAFT — drafted in this session but NOT integrated into phone.py yet,
per the gate: the SMS path it composes against is itself being
CASL-modified in the same branch (sms_order.py). Integrating against a
moving target risks wiring to an unstable base. Once the CASL changes
settle (this branch merged + soaked) AND the Canadian DID is
provisioned, wire the call site marked PAYMENT_LINK_HANDOFF in
phone.py's /gather handler.

Square credentials: uses live production OAuth, not sandbox. Demo
merchant completes Square OAuth via the onboarding wizard like any
other merchant; pos_access_token NULL → logs-only fallback (order in
Supabase, no Square call). Sandbox-CAD-check detour dropped 2026-06-04.

Integration call site (when ready):

    from voice_sms_handoff import send_payment_link_to_caller
    ...
    if tool.name == "submit_order":
        # existing recap + log_call_end ...
        await send_payment_link_to_caller(
            merchant_config=config_row,  # or build one from existing _load_merchant_phone_config result
            order_input=tool.arguments,
            caller_phone=session.get("caller_phone", ""),
        )
        ...
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("meridian.phone_agent.voice_sms_handoff")

# Reuse sidecar helpers — same patterns the SMS path uses, so behaviour
# stays aligned. Path injection mirrors sms_order.py's approach.
_PHONE_AGENT_DIR = str(Path(__file__).resolve().parent)
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

from order_normalizer import normalize_order
from pos_connector import create_pos_order
from payment_links import create_payment_link
from sms_checkout import send_checkout_sms
from casl_compliance import fetch_optout_status


async def send_payment_link_to_caller(
    merchant_config: Any,
    order_input: dict[str, Any],
    caller_phone: str,
    *,
    merchant_id: str,
) -> dict:
    """End-to-end: normalise → POS → payment link → SMS.

    Returns {
        "pos_result":     dict from create_pos_order,
        "payment_link":   dict from create_payment_link,
        "sms_result":     dict from send_checkout_sms (or skipped notice),
        "skipped_reason": str | None,
    }

    Caller-facing behaviour notes:
    - transactional_optout=True → SMS is NOT sent; the caller is
      assumed to want a human handoff or some other channel. POS order
      still placed.
    - marketing_optout=True → SMS IS sent (this is transactional).
    - No caller_phone → SMS skipped; POS order still placed.
    """
    order_input = dict(order_input)
    if caller_phone:
        order_input["caller_phone"] = caller_phone

    normalized = normalize_order(order_input, merchant_config)

    pos_result = await create_pos_order(
        normalized,
        getattr(merchant_config, "pos_system", "") or "",
        getattr(merchant_config, "pos_access_token", "") or "",
        getattr(merchant_config, "pos_location_id", "") or "",
        demo_safe=bool(getattr(merchant_config, "demo_safe", False)),
    )

    payment_link_result: dict = {}
    if getattr(merchant_config, "sms_checkout_enabled", True):
        pos_order_id = pos_result.get("pos_order_id", "")
        payment_link_result = await create_payment_link(
            order=normalized,
            pos_system=getattr(merchant_config, "pos_system", "") or "",
            pos_order_id=pos_order_id,
            access_token=getattr(merchant_config, "pos_access_token", "") or "",
            location_id=getattr(merchant_config, "pos_location_id", "") or "",
        )

    pay_url = payment_link_result.get("url", "")

    sms_result: dict = {}
    skipped_reason: str | None = None

    if not caller_phone:
        skipped_reason = "no_caller_phone"
    elif not pay_url:
        skipped_reason = "no_payment_link"
    else:
        # Transactional opt-out is a hard stop; marketing opt-out is NOT
        # honoured here because the payment link is transactional.
        optout = await fetch_optout_status(merchant_id, caller_phone)
        if optout.get("transactional_optout"):
            skipped_reason = "transactional_optout"
        else:
            sms_result = await send_checkout_sms(
                order=normalized,
                payment_link=pay_url,
                business_name=getattr(merchant_config, "business_name", "")
                    or "Meridian",
            )

    if skipped_reason:
        logger.info(
            "Voice payment-link SMS skipped: merchant=%s phone=%s reason=%s",
            merchant_id, caller_phone, skipped_reason,
        )

    return {
        "pos_result": pos_result,
        "payment_link": payment_link_result,
        "sms_result": sms_result,
        "skipped_reason": skipped_reason,
    }
