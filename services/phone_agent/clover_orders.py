"""
Clover order write path for the phone agent — direct kitchen injection.

Three sequential calls, mirroring what a staff-entered ticket produces:

  1. POST /v3/merchants/{mId}/orders            (state open, Meridian note)
  2. POST .../orders/{orderId}/line_items       (one per UNIT, price in cents)
  3. POST /v3/merchants/{mId}/print_event       (fires the kitchen printer)

Step 3 exists because an API-created Clover order shows in the Orders app but
NEVER prints on its own — Clover only fires the order printer for an explicit
print event. Same mechanism as src/services/pos_connectors/clover_kitchen.py
(website orders); this is the phone-agent leg.

Requires the Clover app to have ORDERS/INVENTORY write permissions (granted at
the app level in the Clover developer dashboard, then a fresh merchant OAuth).
"""
import logging
import os
import re

import httpx

logger = logging.getLogger("meridian.phone_agent.pos.clover")


def clover_api_base() -> str:
    """Region/sandbox-aware Clover API host (mirrors src/config CloverConfig).
    Canada is region 'na' → api.clover.com. CLOVER_API_BASE overrides everything."""
    override = os.getenv("CLOVER_API_BASE", "")
    if override:
        return override.rstrip("/")
    if os.getenv("CLOVER_ENVIRONMENT", "sandbox") != "production":
        return "https://apisandbox.dev.clover.com"
    region = os.getenv("CLOVER_REGION", "na").lower()
    return {
        "na": "https://api.clover.com",
        "eu": "https://api.eu.clover.com",
        "la": "https://api.la.clover.com",
    }.get(region, "https://api.clover.com")


async def create_clover_order(
    order: dict, access_token: str, merchant_id: str, external_ref: str = ""
) -> dict:
    """Create an order in Clover (write), add its line items, then fire the
    kitchen print event. See module docstring for permission prerequisites.

    external_ref: a STABLE per-order id. Set as Clover's externalReferenceId so a
    retry (Vapi re-dispatch, or two workers) of the SAME order does not create a
    second ticket (double-cooked food). Clover rejects the field unless it is
    <=12 chars AND purely alphanumeric, so it is stripped + truncated."""
    base = clover_api_base()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    _body = {
        "state": "open",
        "note": f"Phone order for {order.get('customer_name', '')} via Meridian AI",
    }
    ref_alnum = re.sub(r"[^A-Za-z0-9]", "", str(external_ref or ""))[:12]
    if ref_alnum:
        _body["externalReferenceId"] = ref_alnum

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            f"{base}/v3/merchants/{merchant_id}/orders",
            json=_body,
            headers=headers,
        )
        if res.status_code not in (200, 201):
            logger.warning("Clover order create failed %s: %s", res.status_code, res.text[:300])
            return {"success": False, "reason": "clover_api_error", "status": res.status_code}

        order_id = res.json().get("id", "")

        # One line item per unit so quantity is reflected (the previous code added
        # each item once regardless of quantity → undercharged multi-qty orders).
        added, failed = 0, 0
        for item in order.get("items", []):
            qty = max(1, int(item.get("quantity", 1) or 1))
            price_cents = int(round(float(item.get("unit_price", item.get("price", 0)) or 0) * 100))
            li = {"name": item.get("name", "Item"), "price": price_cents,
                  "note": item.get("special_instructions", "")}
            for _ in range(qty):
                r = await client.post(
                    f"{base}/v3/merchants/{merchant_id}/orders/{order_id}/line_items",
                    json=li, headers=headers,
                )
                if r.status_code in (200, 201):
                    added += 1
                else:
                    failed += 1
                    logger.warning("Clover line-item add failed %s: %s", r.status_code, r.text[:200])

        if added == 0 and failed > 0:
            return {"success": False, "reason": "clover_line_items_failed", "pos_order_id": order_id}

        # Kitchen fire: an API-created Clover order shows in the Orders app but
        # NEVER prints on its own — fire the print event so the ticket lands on
        # the merchant's order printer. Never fatal to the order.
        kitchen_fired, kitchen_fire_status = await _fire_clover_kitchen_print(
            client, base, merchant_id, order_id, headers,
        )

        return {"success": True, "pos_order_id": order_id, "pos_system": "clover",
                "line_items_added": added, "line_items_failed": failed,
                "kitchen_fired": kitchen_fired,
                "kitchen_fire_status": kitchen_fire_status}


async def _fire_clover_kitchen_print(
    client: httpx.AsyncClient,
    base: str,
    merchant_id: str,
    order_id: str,
    headers: dict,
) -> tuple[bool, str]:
    """Fire the kitchen ticket for an API-created Clover order.

    Clover only prints an order when a print event exists for it:
    POST /v3/merchants/{mId}/print_event {"orderRef": {"id": "<orderId>"}}
    (optionally "deviceRef" to target a device). The request is routed to the
    firing device's order printer, or its onboard printer when none is set.

    Print failure must NOT fail the order: many merchants have no printer
    configured or no device online, and the ticket is still visible on the
    register. Returns (kitchen_fired, kitchen_fire_status) where status is the
    HTTP status code as a string, "skipped_disabled" (env kill-switch), or
    "error" (transport exception).
    """
    if os.getenv("CLOVER_KITCHEN_FIRE_ENABLED", "1") == "0":
        logger.info("Clover kitchen fire disabled by env — order %s not printed", order_id)
        return False, "skipped_disabled"
    try:
        res = await client.post(
            f"{base}/v3/merchants/{merchant_id}/print_event",
            json={"orderRef": {"id": order_id}},
            headers=headers,
        )
    except Exception as e:  # noqa: BLE001 — order exists; the print is best-effort
        logger.error("Clover print_event errored for order %s: %s", order_id, e)
        return False, "error"
    if res.status_code in (200, 201):
        logger.info("Clover kitchen ticket fired for order %s", order_id)
        return True, str(res.status_code)
    logger.error(
        "Clover print_event failed %s for order %s — ticket NOT printed "
        "(order still visible in the Orders app): %s",
        res.status_code, order_id, res.text[:300],
    )
    return False, str(res.status_code)
