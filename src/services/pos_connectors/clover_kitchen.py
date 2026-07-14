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
        pay_line = (
            "PAID ONLINE (Stripe) — do not collect" if paid
            else "UNPAID, collect in store"
        )
        lines += ["", f"Total: {float(total):.2f} {currency} — {pay_line}"]

    # Clover order.note caps at 2048 chars; trim rather than 400.
    return "\n".join(lines)[:2000]


async def submit_clover_kitchen_order(
    *,
    access_token: str,
    external_merchant_id: str,
    order: dict,
    source_tag: str = "Meridian Mobile Order",
) -> dict:
    """Create the order in Clover, attach line items, then fire it to the
    kitchen printer. Returns
    {success, pos_order_id, kitchen_print_fired, reason?}.

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

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.post(
            f"{base}/orders",
            json={
                "state": "open",
                "title": source_tag,
                "note": note,
                "manualTransaction": False,
            },
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
        for item in order.get("items", []):
            unit_price = float(item.get("price", item.get("unit_price", 0)) or 0)
            special = (item.get("special_instructions") or item.get("notes") or "").strip()
            li = {
                "name": str(item.get("name", "Item"))[:127],
                "price": int(round(unit_price * 100)),
            }
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
        try:
            pe_res = await client.post(
                f"{base}/print_event",
                json={"orderRef": {"id": pos_order_id}},
                headers=headers,
            )
            kitchen_print_fired = pe_res.status_code in (200, 201)
            if not kitchen_print_fired:
                logger.warning(
                    "clover kitchen: print_event failed HTTP %s for order %s "
                    "(order still on register)",
                    pe_res.status_code, pos_order_id,
                )
        except Exception as e:  # noqa: BLE001 — order exists; print is best-effort
            logger.warning("clover kitchen: print_event error for %s: %s", pos_order_id, e)

    return {
        "success": True,
        "pos_order_id": pos_order_id,
        "kitchen_print_fired": kitchen_print_fired,
    }


def _safe_qty(item: dict) -> int:
    try:
        return max(1, min(int(item.get("quantity", 1)), MAX_LINE_ITEMS))
    except (TypeError, ValueError):
        return 1


def _short_ref(order: dict) -> str:
    ref = str(order.get("order_ref") or order.get("id") or "")
    return ref[:8].upper() if ref else "NEW"
