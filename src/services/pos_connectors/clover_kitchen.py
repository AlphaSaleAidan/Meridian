"""
Clover Kitchen Submitter — lands a Meridian order in a merchant's Clover POS
the way a normal ticket does: an OPEN order carrying a Meridian source tag in
its title, a human-readable note (customer, type, per-item instructions), real
line items, and a print_event so the ticket fires to the kitchen order printer.

Why this exists instead of GenericRESTConnector: Clover order creation is
three sequential calls (order → line_items → print_event), and an API-created
order does NOT print to the kitchen unless a print event is explicitly
created for it — the generic single-POST connector can't express that.
"""
import logging
import os
import re

import httpx

logger = logging.getLogger("meridian.pos.clover_kitchen")


def clover_api_base() -> str:
    """Region/environment-aware Clover host — same contract as the phone
    sidecar's pos_connector.clover_api_base (CLOVER_ENVIRONMENT=sandbox for
    dev merchants)."""
    if os.environ.get("CLOVER_ENVIRONMENT", "").strip().lower() == "sandbox":
        return "https://apisandbox.dev.clover.com"
    return "https://api.clover.com"

# Hard ceiling on line items created per order (quantity expansion included)
# so a malformed payload can't hammer the merchant's Clover account.
MAX_LINE_ITEMS = 50

_TIMEOUT = 15


def build_kitchen_note(order: dict, source_tag: str) -> str:
    """Human-readable ticket note: who ordered, how it goes out, and exactly
    what to make — mirrors what staff would key in themselves."""
    customer = (order.get("customer_name") or "").strip() or "Customer"
    phone = (order.get("customer_phone") or "").strip()
    who = f"{customer} ({phone})" if phone else customer

    lines = [
        f"{source_tag} #{_short_ref(order)}",
        f"Customer: {who}",
        f"Type: {(order.get('order_type') or 'pickup').upper()}",
        "",
    ]
    for item in order.get("items", []):
        qty = _safe_qty(item)
        line = f"{qty}x {item.get('name', 'Item')}"
        special = (item.get("special_instructions") or item.get("notes") or "").strip()
        if special:
            line += f" — {special}"
        lines.append(line)

    if (order.get("special_instructions") or "").strip():
        lines += ["", f"Notes: {order['special_instructions'].strip()}"]

    total = order.get("total")
    if total is not None:
        currency = order.get("currency") or ""
        # Payment state must be unmissable on the ticket: staff either collect
        # in store or hand the bag over, and the wrong guess costs real money.
        paid = order.get("status") == "paid" or bool(order.get("paid"))
        is_cash = (order.get("payment_method") or "").strip().lower() == "cash"
        if paid:
            pay_line = "PAID ONLINE (Stripe) — do not collect"
        elif is_cash:
            # Pay-with-cash order: staff collect cash on pickup, no online charge.
            pay_line = "UNPAID — CASH ON PICKUP, collect cash in store"
        else:
            pay_line = "UNPAID, collect in store"
        lines += ["", f"Total: {float(total):.2f} {currency} — {pay_line}"]

    # Clover order.note caps at 2048 chars; trim rather than 400.
    return "\n".join(lines)[:2000]


def _clover_item_id_for(item: dict, item_id_map: dict | None) -> str:
    """Resolve an order item to the merchant's Clover inventory itemId.

    Prefer an explicit id stored on the order item (``clover_item_id`` /
    ``pos_item_id`` / ``source_external_id``, e.g. threaded from the menu row),
    then fall back to a lower(name) lookup in ``item_id_map`` (built from the
    merchant's POS-imported menu items). Returns "" when nothing maps — the
    caller then sends a freeform name+price line item, never blocking the order
    on a missing mapping.
    """
    for key in ("clover_item_id", "pos_item_id", "source_external_id"):
        val = item.get(key)
        if val:
            return str(val).strip()
    if item_id_map:
        name = str(item.get("name", "")).strip().lower()
        if name:
            return str(item_id_map.get(name) or "").strip()
    return ""


async def submit_clover_kitchen_order(
    *,
    access_token: str,
    external_merchant_id: str,
    order: dict,
    source_tag: str = "Meridian Mobile Order",
    item_id_map: dict | None = None,
) -> dict:
    """Create the order in Clover, attach line items, then fire it to the
    kitchen printer. Returns
    {success, pos_order_id, kitchen_print_fired, line_items_mapped?, reason?}.

    ``item_id_map`` is an optional {lower(name): clover_item_id} map (the
    merchant's POS-imported inventory). When an order item resolves to a real
    Clover itemId, the line item carries ``{"item": {"id": <id>}}`` so the sale
    books against real inventory and shows up in the merchant's Clover sales
    reports — otherwise we send the current freeform name+price line item. A
    missing/failed mapping NEVER blocks an order.

    Print-event failure is non-fatal: the order still exists on the register,
    so we report success with kitchen_print_fired=False and let staff see it
    in the Orders app.
    """
    if not (access_token or "").strip() or not (external_merchant_id or "").strip():
        return {"success": False, "reason": "missing_clover_credentials"}

    base = f"{clover_api_base()}/v3/merchants/{external_merchant_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    note = build_kitchen_note(order, source_tag)

    customer = (order.get("customer_name") or "").strip()
    # Customer name in the title so the register's order list shows WHO at a
    # glance (parity with Square's fulfillment recipient).
    title = f"{source_tag} — {customer}"[:120] if customer else source_tag
    order_ref = str(order.get("order_ref") or order.get("id") or "")

    order_body = {
        "state": "open",
        "title": title,
        "note": note,
        "manualTransaction": False,
    }
    # Traceability + dedup handle: ties the Clover order back to the Meridian
    # order id (parity with Square's reference_id). Clover treats this as the
    # Invoice ID and REJECTS the whole order create unless it's <=12 chars AND
    # purely alphanumeric — a hyphen (every UUID has one by char 9) 400s with
    # the misleading "Invoice ID cannot exceed 12 characters". Probed live
    # 2026-07-21: 12 alnum → 200, 12 with hyphen → 400, so strip + cut.
    ref_alnum = re.sub(r"[^A-Za-z0-9]", "", order_ref)[:12]
    if ref_alnum:
        order_body["externalReferenceId"] = ref_alnum

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.post(
            f"{base}/orders",
            json=order_body,
            headers=headers,
        )
        if res.status_code not in (200, 201):
            logger.warning(
                "clover kitchen: order create failed HTTP %s: %s",
                res.status_code, res.text[:200],
            )
            return {
                "success": False,
                "reason": f"clover_order_http_{res.status_code}",
            }

        pos_order_id = (res.json() or {}).get("id", "")

        created = 0
        mapped = 0
        for item in order.get("items", []):
            unit_price = float(item.get("price", item.get("unit_price", 0)) or 0)
            special = (item.get("special_instructions") or item.get("notes") or "").strip()
            li = {
                "name": str(item.get("name", "Item"))[:127],
                "price": int(round(unit_price * 100)),
            }
            # Sales-reporting parity: when this order item maps to a real Clover
            # inventory item, book the line against it. Name + price still ride
            # along (Clover keeps the override), so an unmapped item is simply
            # the current freeform behavior — a missing map never blocks.
            clover_item_id = _clover_item_id_for(item, item_id_map)
            if clover_item_id:
                li["item"] = {"id": clover_item_id}
                mapped += 1
            if special:
                li["note"] = special[:255]
            # Clover line items are one row per unit — expand quantity.
            for _ in range(_safe_qty(item)):
                if created >= MAX_LINE_ITEMS:
                    logger.warning(
                        "clover kitchen: line item cap %s hit for order %s",
                        MAX_LINE_ITEMS, pos_order_id,
                    )
                    break
                li_res = await client.post(
                    f"{base}/orders/{pos_order_id}/line_items",
                    json=li,
                    headers=headers,
                )
                if li_res.status_code not in (200, 201):
                    logger.warning(
                        "clover kitchen: line item failed HTTP %s on order %s",
                        li_res.status_code, pos_order_id,
                    )
                created += 1

        kitchen_print_fired = False
        kitchen_print_reason = ""
        try:
            pe_res = await client.post(
                f"{base}/print_event",
                json={"orderRef": {"id": pos_order_id}},
                headers=headers,
            )
            kitchen_print_fired = pe_res.status_code in (200, 201)
            if not kitchen_print_fired:
                # Clover 400s "The default printing device is missing" when the
                # merchant has no default order printer set on their register —
                # a config state, not a fault (verified live 2026-07-21; no API
                # workaround, explicit deviceRef/printerRef doesn't bypass it).
                # The order is on the register either way; staff see it in the
                # Orders app. Surface a stable reason so onboarding/support can
                # tell the merchant to set their kitchen printer as default.
                body = pe_res.text[:200]
                if "default printing device" in body.lower():
                    kitchen_print_reason = "no_default_printer"
                    logger.info(
                        "clover kitchen: merchant %s has no default order "
                        "printer — order %s on register, no auto ticket",
                        external_merchant_id, pos_order_id,
                    )
                else:
                    kitchen_print_reason = f"print_event_http_{pe_res.status_code}"
                    logger.warning(
                        "clover kitchen: print_event failed HTTP %s for order %s "
                        "(order still on register): %s",
                        pe_res.status_code, pos_order_id, body,
                    )
        except Exception as e:  # noqa: BLE001 — order exists; print is best-effort
            kitchen_print_reason = "print_event_error"
            logger.warning("clover kitchen: print_event error for %s: %s", pos_order_id, e)

    result = {
        "success": True,
        "pos_order_id": pos_order_id,
        "kitchen_print_fired": kitchen_print_fired,
        # How many distinct order items booked against real Clover inventory
        # (support/observability — 0 means every line was freeform).
        "line_items_mapped": mapped,
    }
    if kitchen_print_reason:
        result["kitchen_print_reason"] = kitchen_print_reason
    return result


def _safe_qty(item: dict) -> int:
    try:
        return max(1, min(int(item.get("quantity", 1)), MAX_LINE_ITEMS))
    except (TypeError, ValueError):
        return 1


def _short_ref(order: dict) -> str:
    ref = str(order.get("order_ref") or order.get("id") or "")
    return ref[:8].upper() if ref else "NEW"
