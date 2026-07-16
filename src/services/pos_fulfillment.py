"""
POS fulfillment verification — the "did it actually reach the kitchen?" check.

After a POS create succeeds we only know the API accepted the payload. This
module confirms the order reached a MAKE-ABLE state on the POS side and records
the proof on phone_orders (fulfillment_state + fulfillment_confirmed_at).

Structured per-POS so verifiers slot in as integrations mature:

  square → implemented: poll GET /v2/orders/{id} for state OPEN (or COMPLETED)
           with line items present, a few retries over ~30s.
  toast  → stub ("unsupported") — Toast order-read integration pending.
  clover → stub ("unsupported") — order injection itself is blocked on App
           Market approval; SMS covers Clover merchants today.

The Square order.updated webhook (src/api/routes/webhooks.py →
_update_phone_order_fulfillment) provides the ongoing feed after this one-shot
poll: kitchen/KDS state changes keep flowing onto the same columns.
"""
import asyncio
import logging
from datetime import datetime, timezone

from ..square.client import SquareClient

logger = logging.getLogger("meridian.services.pos_fulfillment")

# States in which a Square order is (or was) make-able by the kitchen.
_SQUARE_CONFIRMED_STATES = {"OPEN", "COMPLETED"}

DEFAULT_ATTEMPTS = 6
DEFAULT_DELAY_SECONDS = 5.0  # 6 × 5s ≈ 30s window


async def verify_fulfillment(
    pos_system: str,
    pos_order_id: str,
    access_token: str,
    location_id: str = "",
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> dict:
    """Confirm a POS order reached a make-able state.

    Returns {"supported": bool, "confirmed": bool, "state": str, "detail": str}.
    Never raises — a verification hiccup must not break order flow.
    """
    system = (pos_system or "").strip().lower()
    if not pos_order_id:
        return {"supported": True, "confirmed": False, "state": "no_pos_order",
                "detail": "no POS order id to verify"}
    if system == "square":
        return await _verify_square(
            pos_order_id, access_token, location_id,
            attempts=attempts, delay_seconds=delay_seconds,
        )
    # Toast / Clover / generic: no read-back verifier yet. Explicitly
    # "unsupported" (≠ failed) so the UI can say "check the printer" honestly.
    return {"supported": False, "confirmed": False, "state": "unsupported",
            "detail": f"no fulfillment verifier for pos_system={system or 'none'}"}


async def _verify_square(
    pos_order_id: str,
    access_token: str,
    location_id: str,
    *,
    attempts: int,
    delay_seconds: float,
) -> dict:
    """Poll Square for the order until it is OPEN with line items present.

    The phone-agent connector creates orders against the production Square
    host (services/phone_agent/pos_connector.py), so the verifier reads from
    production too — a sandbox-configured SquareClient would 404 the order.
    """
    if not access_token:
        return {"supported": True, "confirmed": False, "state": "no_token",
                "detail": "no Square access token available for verification"}

    client = SquareClient(access_token=access_token, environment="production")
    last_state, last_detail = "unknown", ""
    try:
        for attempt in range(max(1, attempts)):
            if attempt:
                await asyncio.sleep(delay_seconds)
            try:
                order = await client.get_order(pos_order_id)
            except Exception as e:  # noqa: BLE001 — keep polling through blips
                last_detail = str(e)
                logger.warning("Square fulfillment poll %d/%d failed for %s: %s",
                               attempt + 1, attempts, pos_order_id, e)
                continue
            last_state = order.get("state", "") or "unknown"
            has_items = bool(order.get("line_items"))
            if last_state in _SQUARE_CONFIRMED_STATES and has_items:
                logger.info("Square order %s confirmed make-able (state=%s, %d items)",
                            pos_order_id, last_state, len(order.get("line_items", [])))
                return {"supported": True, "confirmed": True, "state": last_state,
                        "detail": f"{len(order.get('line_items', []))} line item(s)"}
            if last_state in ("CANCELED",):
                return {"supported": True, "confirmed": False, "state": last_state,
                        "detail": "order was canceled on the POS side"}
            last_detail = ("no line items on order" if not has_items
                           else f"state={last_state}")
    finally:
        await client.close()

    return {"supported": True, "confirmed": False, "state": last_state,
            "detail": last_detail or "not confirmed within the polling window"}


async def verify_and_record(
    pos_system: str,
    pos_order_id: str,
    access_token: str,
    phone_order_id: str,
    location_id: str = "",
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> dict:
    """Run verification and persist the result onto the phone_orders row.

    Intended for FastAPI BackgroundTasks: the caller responds immediately and
    the status endpoint / frontend polls the row for the outcome.
    """
    result = await verify_fulfillment(
        pos_system, pos_order_id, access_token, location_id,
        attempts=attempts, delay_seconds=delay_seconds,
    )
    if phone_order_id:
        try:
            from ..db import get_db
            patch: dict = {"fulfillment_state": result["state"]}
            if result["confirmed"]:
                patch["fulfillment_confirmed_at"] = datetime.now(timezone.utc).isoformat()
            await get_db().update(
                "phone_orders", patch, filters={"id": f"eq.{phone_order_id}"},
            )
        except Exception as e:  # noqa: BLE001 — recording failure only degrades the UI
            logger.error("could not record fulfillment for phone order %s: %s",
                         phone_order_id, e)
    return result
