"""
Payment link generator — creates checkout URLs from connected POS systems.
Square, Toast, and Clover have native payment link APIs.
All other POS systems get a Meridian-hosted checkout page.
"""
import logging
import os
import uuid
from typing import Any

import httpx

logger = logging.getLogger("meridian.phone_agent.payments")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
MERIDIAN_CHECKOUT_BASE = os.getenv("MERIDIAN_CHECKOUT_URL", "https://pay.meridian.ai")

# UNIFIED PAYMENTS (Stripe Connect): one processor across any POS. Gated off by
# default so the live per-POS payment-link flow is unchanged until this is
# validated in Stripe test mode and turned on.
UNIFIED_PAYMENTS_ENABLED = os.getenv("UNIFIED_PAYMENTS_ENABLED", "0") == "1"
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
# Meridian's platform fee in basis points (100 = 1%). Default 0 = no fee.
PLATFORM_FEE_BPS = int(os.getenv("MERIDIAN_PLATFORM_FEE_BPS", "0") or 0)
SUCCESS_URL = os.getenv("CHECKOUT_SUCCESS_URL", "https://meridian.tips/pay/success")


def _stripe():
    """Lazy stripe client so the module imports with no SDK/key present."""
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def _order_amount_cents(order: dict[str, Any]) -> int:
    """Total in cents — prefer the order total, else sum item prices."""
    total = order.get("total")
    if total:
        return int(round(float(total) * 100))
    cents = 0
    for i in order.get("items", []):
        price = i.get("unit_price", i.get("price", 0)) or 0
        cents += int(round(float(price) * 100)) * int(i.get("quantity", 1) or 1)
    return cents


def _stripe_line_items(order: dict[str, Any], currency: str) -> list[dict]:
    """Itemized Stripe line_items when items carry prices; else a single
    order-total line (charges the correct amount either way)."""
    items, ok = [], True
    for i in order.get("items", []):
        price = i.get("unit_price", i.get("price"))
        if price is None:
            ok = False
            break
        name = i.get("name", "Item")
        if i.get("size"):
            name += f" ({i['size']})"
        items.append({
            "quantity": int(i.get("quantity", 1) or 1),
            "price_data": {
                "currency": currency,
                "unit_amount": int(round(float(price) * 100)),
                "product_data": {"name": name},
            },
        })
    if ok and items:
        return items
    return [{
        "quantity": 1,
        "price_data": {
            "currency": currency,
            "unit_amount": _order_amount_cents(order),
            "product_data": {"name": "Phone order"},
        },
    }]


async def create_checkout(order: dict[str, Any], merchant_config, pos_order_id: str = "") -> dict:
    """Preferred checkout entry point. When unified payments are on and a Stripe
    key is configured, ALWAYS produce a real Stripe hosted-checkout link:
      • merchant onboarded for Connect → destination charge to their account
        (+ Meridian application fee);
      • not onboarded yet (demo / pre-Connect) → direct charge on Meridian's own
        platform account, so the customer can still pay now (no dead link).
    Stripe supports CAD, so this is the rail that actually works for Canada — the
    per-POS fallback below stranded CAD orders on a non-existent checkout page.
    Same return shape ({url, method, ...}) so callers/SMS are unchanged."""
    if UNIFIED_PAYMENTS_ENABLED and STRIPE_SECRET_KEY:
        try:
            acct = getattr(merchant_config, "stripe_account_id", "")
            charges_ok = getattr(merchant_config, "stripe_charges_enabled", False)
            connect_account = acct if (acct and charges_ok) else ""
            return await _stripe_checkout(order, merchant_config, pos_order_id, connect_account)
        except Exception as e:  # noqa: BLE001 — never strand the order; fall back
            logger.error("Stripe checkout failed, falling back to POS link: %s", e)
    return await create_payment_link(
        order,
        getattr(merchant_config, "pos_system", "") or "",
        pos_order_id,
        getattr(merchant_config, "pos_access_token", "") or "",
        getattr(merchant_config, "pos_location_id", "") or "",
    )


async def _stripe_checkout(
    order: dict[str, Any], merchant_config, pos_order_id: str, connect_account: str = ""
) -> dict:
    """Stripe hosted Checkout (POS-agnostic). With `connect_account` → a
    destination charge to that connected account + Meridian application fee.
    Without one → a direct charge on Meridian's platform account so unboarded
    merchants (and the demo) can still take payment immediately."""
    stripe = _stripe()
    currency = (order.get("currency") or "cad").lower()
    amount = _order_amount_cents(order)

    kwargs: dict[str, Any] = dict(
        mode="payment",
        line_items=_stripe_line_items(order, currency),
        success_url=SUCCESS_URL,
        client_reference_id=pos_order_id or order.get("merchant_id", ""),
        metadata={
            "merchant_id": order.get("merchant_id", ""),
            "pos_order_id": pos_order_id,
            "caller_phone": order.get("caller_phone", ""),
        },
    )
    if connect_account:
        pi_data: dict[str, Any] = {"transfer_data": {"destination": connect_account}}
        if PLATFORM_FEE_BPS > 0:
            pi_data["application_fee_amount"] = int(round(amount * PLATFORM_FEE_BPS / 10000))
        kwargs["payment_intent_data"] = pi_data

    session = stripe.checkout.Session.create(**kwargs)
    # Stripe SDK objects are NOT dicts — use subscript access, not .get()
    # (.get raises AttributeError on a StripeObject).
    await _record_checkout_session(order, merchant_config, pos_order_id, session, amount, currency)
    logger.info("Stripe checkout %s (%s) for merchant %s ($%.2f %s)",
                session["id"], "connect" if connect_account else "platform",
                order.get("merchant_id"), amount / 100, currency.upper())
    return {"url": session["url"], "method": "stripe", "link_id": session["id"], "session_id": session["id"]}


async def _record_checkout_session(order, merchant_config, pos_order_id, session, amount, currency) -> None:
    if not (SUPABASE_URL and SUPABASE_KEY):
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/checkout_sessions",
                json={
                    "merchant_id": order.get("merchant_id", ""),
                    "pos_order_id": pos_order_id,
                    "provider": "stripe",
                    "provider_ref": session["id"],
                    "amount_cents": amount,
                    "currency": currency,
                    "status": "created",
                    "checkout_url": session["url"],
                    "caller_phone": order.get("caller_phone", ""),
                },
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                         "Content-Type": "application/json", "Prefer": "return=minimal"},
            )
    except Exception as e:  # noqa: BLE001 — recording is best-effort
        logger.warning("checkout_sessions insert failed: %s", e)


async def create_payment_link(
    order: dict[str, Any],
    pos_system: str,
    pos_order_id: str,
    access_token: str,
    location_id: str,
) -> dict:
    """
    Generate a payment link for a phone order.
    Returns {"url": "...", "method": "square|toast|clover|meridian"} on success.
    """
    if not pos_system:
        return await _create_meridian_checkout(order)

    try:
        if pos_system == "square":
            return await _square_payment_link(order, access_token, location_id, pos_order_id)
        elif pos_system == "toast":
            return await _toast_payment_link(order, access_token, location_id, pos_order_id)
        elif pos_system == "clover":
            return await _clover_payment_link(order, access_token, location_id, pos_order_id)
        else:
            return await _create_meridian_checkout(order, pos_system)
    except Exception as e:
        logger.error("Payment link creation failed for %s: %s", pos_system, e)
        return await _create_meridian_checkout(order, pos_system)


async def _square_payment_link(
    order: dict, access_token: str, location_id: str, pos_order_id: str
) -> dict:
    line_items = []
    for item in order.get("items", []):
        line_items.append({
            "name": item["name"],
            "quantity": str(item.get("quantity", 1)),
            "base_price_money": {
                "amount": int(item.get("unit_price", 0) * 100),
                "currency": order.get("currency", "USD"),
            },
        })

    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "quick_pay": None,
        "order": {
            "location_id": location_id,
            "line_items": line_items,
            "reference_id": pos_order_id,
        },
        "checkout_options": {
            "redirect_url": f"{MERIDIAN_CHECKOUT_BASE}/confirmation/{pos_order_id}",
            "ask_for_shipping_address": order.get("order_type") == "delivery",
        },
        "pre_populated_data": {
            "buyer_phone": order.get("caller_phone", ""),
        },
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://connect.squareup.com/v2/online-checkout/payment-links",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Square-Version": "2024-01-18",
            },
            timeout=10,
        )
        if res.status_code in (200, 201):
            data = res.json()
            url = data.get("payment_link", {}).get("url", "")
            link_id = data.get("payment_link", {}).get("id", "")
            logger.info("Square payment link created: %s", link_id)
            return {"url": url, "link_id": link_id, "method": "square"}
        else:
            logger.warning("Square payment link error %d: %s", res.status_code, res.text[:300])
            return await _create_meridian_checkout(order, "square")


async def _toast_payment_link(
    order: dict, access_token: str, location_id: str, pos_order_id: str
) -> dict:
    payload = {
        "orderGuid": pos_order_id,
        "amount": int(order.get("total", 0) * 100),
        "customerPhone": order.get("caller_phone", ""),
        "redirectUrl": f"{MERIDIAN_CHECKOUT_BASE}/confirmation/{pos_order_id}",
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://toast-api-server/orders/v2/paymentLinks",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Toast-Restaurant-External-ID": location_id,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if res.status_code in (200, 201):
            data = res.json()
            url = data.get("paymentUrl", data.get("url", ""))
            logger.info("Toast payment link created for order %s", pos_order_id)
            return {"url": url, "link_id": pos_order_id, "method": "toast"}
        else:
            logger.warning("Toast payment link error %d", res.status_code)
            return await _create_meridian_checkout(order, "toast")


async def _clover_payment_link(
    order: dict, access_token: str, merchant_id: str, pos_order_id: str
) -> dict:
    payload = {
        "amount": int(order.get("total", 0) * 100),
        "note": f"Phone order for {order.get('customer_name', '')}",
        "redirectUrl": f"{MERIDIAN_CHECKOUT_BASE}/confirmation/{pos_order_id}",
        "customer": {
            "phoneNumber": order.get("caller_phone", ""),
        },
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api.clover.com/v3/merchants/{merchant_id}/pay_links",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if res.status_code in (200, 201):
            data = res.json()
            url = data.get("url", data.get("paymentUrl", ""))
            link_id = data.get("id", "")
            logger.info("Clover payment link created: %s", link_id)
            return {"url": url, "link_id": link_id, "method": "clover"}
        else:
            logger.warning("Clover payment link error %d", res.status_code)
            return await _create_meridian_checkout(order, "clover")


async def _create_meridian_checkout(order: dict, pos_system: str = "") -> dict:
    """
    Create a Meridian-hosted checkout page for POS systems without
    native payment link APIs. Saves a checkout session to Supabase
    and returns the URL.
    """
    checkout_id = str(uuid.uuid4())[:12]

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/checkout_sessions",
                    json={
                        "id": checkout_id,
                        "merchant_id": order.get("merchant_id", ""),
                        "customer_name": order.get("customer_name", ""),
                        "customer_phone": order.get("caller_phone", ""),
                        "order_type": order.get("order_type", "pickup"),
                        "items": order.get("items", []),
                        "subtotal": order.get("subtotal", 0),
                        "tax": order.get("tax", 0),
                        "total": order.get("total", 0),
                        "currency": order.get("currency", "USD"),
                        "pos_system": pos_system,
                        "status": "pending",
                        "source": "phone_agent",
                    },
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    },
                    timeout=10,
                )
        except Exception as e:
            logger.error("Failed to create checkout session: %s", e)

    url = f"{MERIDIAN_CHECKOUT_BASE}/checkout/{checkout_id}"
    logger.info("Meridian checkout created: %s (pos=%s)", checkout_id, pos_system or "none")
    return {"url": url, "link_id": checkout_id, "method": "meridian"}
