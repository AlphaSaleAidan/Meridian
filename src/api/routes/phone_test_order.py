"""
Kitchen prove-out — send a clearly-marked TEST ORDER through the REAL dispatch
path and confirm it lands.

  POST /api/phone/test-order/{merchant_id}
      → builds a "MERIDIAN TEST ORDER" (one cheap real menu item, or a $0.01
        line) and runs it through pay_on_phone.dispatch_order — the exact
        pipeline live calls use, so it exercises the merchant's real POS creds
        and honors demo_safe (logs-only, no live POS write). Returns per-channel
        results immediately + the phone_orders row id; a background task then
        polls the POS (Square) to confirm the ticket reached a make-able state.

  GET  /api/phone/test-order/{merchant_id}/status/{order_id}
      → per-channel delivery status + fulfillment confirmation for the
        onboarding UI to poll.

The test order is forced to pay_at_pickup semantics (POS ticket pushes NOW —
deferring it behind a payment would prove nothing) with the customer pay-link
SMS disabled (no payment links for a fake order); the merchant-notification SMS
leg stays on so the SMS channel is proven too.
"""
import dataclasses
import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..auth import enforce_service_member, require_service_auth
from ...db import get_db
from .phone_dashboard import _validate_merchant_id

# Phone-agent modules live in a sibling dir (same sys.path trick as
# vapi_webhook.py / phone.py).
_PHONE_AGENT_DIR = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

logger = logging.getLogger("meridian.api.phone_test_order")

router = APIRouter(prefix="/api/phone/test-order", tags=["phone-test-order"])


def _square_env_fallback(config) -> tuple[str, str]:
    """Token/location used for the POS push — mirrors the dispatch path's env
    fallback (delivery_channels.create_pos_for_config) so the verifier reads
    the same account the ticket was created in."""
    token = getattr(config, "pos_access_token", "") or ""
    location = getattr(config, "pos_location_id", "") or ""
    if (getattr(config, "pos_system", "") or "") == "square" and not token:
        token = os.getenv("SQUARE_ACCESS_TOKEN", "")
        location = location or os.getenv("SQUARE_LOCATION_ID", "")
    return token, location


@router.post("/{merchant_id}")
async def send_test_order(
    merchant_id: str,
    background_tasks: BackgroundTasks,
    principal=Depends(require_service_auth),
):
    """Fire a clearly-marked test order through the live dispatch pipeline."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)

    from delivery_channels import build_test_order  # type: ignore[import]
    from merchant_config import get_merchant_config  # type: ignore[import]
    from pay_on_phone import dispatch_order  # type: ignore[import]

    config = await get_merchant_config(merchant_id)
    if config is None:
        raise HTTPException(404, "No phone config found for this merchant — finish setup first")

    # Force release-now semantics for the prove-out: the whole point is a
    # ticket in the kitchen NOW. No customer pay-link for a fake order; the
    # merchant-notification SMS leg stays on (it proves the SMS channel).
    test_config = dataclasses.replace(
        config, payment_mode="pay_at_pickup", sms_checkout_enabled=False,
    )
    order = build_test_order(test_config)

    routed = await dispatch_order(order, test_config, {"phone": ""})
    delivery = routed.get("delivery") or {}
    pos_leg = delivery.get("pos") or {}
    pos_result = routed.get("pos_result") or {}
    phone_order_id = routed.get("phone_order_id")

    # Kitchen prove-out: when the ticket actually reached the POS, verify it in
    # the background (Square: poll until OPEN + line items; Clover: poll until
    # open + line items — for Clover the location slot carries the merchant id;
    # others record 'unsupported'). The status endpoint surfaces the result.
    verifying = False
    if pos_leg.get("status") == "sent" and pos_result.get("pos_order_id") and phone_order_id:
        from ...services.pos_fulfillment import verify_and_record
        token, location = _square_env_fallback(config)
        background_tasks.add_task(
            verify_and_record,
            order.get("pos_system", ""),
            pos_result.get("pos_order_id", ""),
            token,
            phone_order_id,
            location,
        )
        verifying = True

    logger.info(
        "Test order dispatched: merchant=%s pos=%s merchant_sms=%s demo_safe=%s row=%s",
        merchant_id, pos_leg.get("status"),
        (delivery.get("merchant_sms") or {}).get("status"),
        bool(getattr(config, "demo_safe", False)), phone_order_id,
    )

    return {
        "ok": True,
        "order_id": phone_order_id,
        "pos_order_id": pos_result.get("pos_order_id", ""),
        "pos_system": order.get("pos_system", ""),
        "demo_safe": bool(getattr(config, "demo_safe", False)),
        "verifying": verifying,
        "channels": {
            "pos": delivery.get("pos"),
            "customer_sms": delivery.get("customer_sms"),
            "merchant_sms": delivery.get("merchant_sms"),
        },
        "item": (order.get("items") or [{}])[0].get("name", ""),
        "total": order.get("total", 0),
    }


@router.get("/{merchant_id}/status/{order_id}")
async def test_order_status(
    merchant_id: str,
    order_id: str,
    principal=Depends(require_service_auth),
):
    """Per-channel delivery status + fulfillment confirmation for polling."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)

    db = get_db()
    rows = await db.select(
        "phone_orders",
        filters={"id": f"eq.{order_id}", "merchant_id": f"eq.{merchant_id}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "Order not found")
    row = rows[0]

    return {
        "order_id": row.get("id"),
        "source": row.get("source"),
        "status": row.get("status"),
        "pos_system": row.get("pos_system"),
        "pos_order_id": row.get("pos_order_id"),
        "pos_success": row.get("pos_success"),
        "pos_delivery_status": row.get("pos_delivery_status"),
        "sms_delivery_status": row.get("sms_delivery_status"),
        "merchant_notify_status": row.get("merchant_notify_status"),
        "delivery_detail": row.get("delivery_detail") or {},
        "fulfillment_state": row.get("fulfillment_state"),
        "fulfillment_confirmed_at": row.get("fulfillment_confirmed_at"),
        "created_at": row.get("created_at"),
    }
