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
# Server-side writes (checkout_sessions for the branded /p/<code> short link) must
# use the service-role key — the anon role lacks INSERT (→ 401 "permission
# denied"), which silently dropped the short link and texted the long Stripe URL.
# Matches src/db get_db()'s key selection; anon kept only as a last-resort fallback.
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.getenv("SUPABASE_SERVICE_KEY", "")
    or os.getenv("SUPABASE_ANON_KEY", "")
)
MERIDIAN_CHECKOUT_BASE = os.getenv("MERIDIAN_CHECKOUT_URL", "https://pay.meridian.ai")

# UNIFIED PAYMENTS (Stripe Connect): one processor across any POS. Gated off by
# default so the live per-POS payment-link flow is unchanged until this is
# validated in Stripe test mode and turned on.
UNIFIED_PAYMENTS_ENABLED = os.getenv("UNIFIED_PAYMENTS_ENABLED", "0") == "1"
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
# Meridian's platform fee in basis points (100 = 1%). Default 0 = no fee.
PLATFORM_FEE_BPS = int(os.getenv("MERIDIAN_PLATFORM_FEE_BPS", "0") or 0)
# Flat per-order service fee in cents (e.g. the premium voice-agent fee). Taken
# as the Stripe application fee on the destination charge — it lands in
# Meridian's balance and the merchant is auto-paid the remainder (Stripe payout
# schedule, set to daily at onboarding). Combined with PLATFORM_FEE_BPS if both set.
SERVICE_FEE_CENTS = int(os.getenv("MERIDIAN_SERVICE_FEE_CENTS", "0") or 0)
# Demo test-charge override: when set, orders for a demo merchant charge this flat
# amount (clamped to Stripe's $0.50 CAD minimum) instead of the real total, so
# test runs cost ~$0.50 rather than full price. Real merchants are never touched.
DEMO_TEST_CHARGE_CENTS = int(os.getenv("MERIDIAN_DEMO_TEST_CHARGE_CENTS", "0") or 0)
_DEMO_MERCHANT_IDS = {"demo", "demo-merchant", "demo-tryout"}
# Base for the branded short pay link (<base>/p/<code> -> Stripe checkout URL).
# Served by the backend /p/{code} redirect route.
PUBLIC_PAY_BASE = os.getenv("PUBLIC_PAY_BASE", "https://api.meridian.tips").rstrip("/")
# Post-checkout pages are served by the backend (api.meridian.tips), NOT the
# frontend SPA — the old default pointed at meridian.tips/pay/success which has
# no route, so the SPA served the home page after payment. {CHECKOUT_SESSION_ID}
# is substituted by Stripe so the success page can show the CAD amount paid.
SUCCESS_URL = os.getenv(
    "CHECKOUT_SUCCESS_URL", f"{PUBLIC_PAY_BASE}/pay/success?session_id={{CHECKOUT_SESSION_ID}}")
CANCEL_URL = os.getenv("CHECKOUT_CANCEL_URL", f"{PUBLIC_PAY_BASE}/pay/cancel")


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

    # Demo test-charge override → flat ~$0.50 line instead of the real total.
    if DEMO_TEST_CHARGE_CENTS and order.get("merchant_id", "") in _DEMO_MERCHANT_IDS:
        amount = max(50, DEMO_TEST_CHARGE_CENTS)  # Stripe CAD minimum is 50¢
        line_items = [{"quantity": 1, "price_data": {
            "currency": currency, "unit_amount": amount,
            "product_data": {"name": "Demo test charge"}}}]
        logger.info("DEMO test-charge override: charging %d¢ (merchant=%s)",
                    amount, order.get("merchant_id"))
    else:
        line_items = _stripe_line_items(order, currency)

    kwargs: dict[str, Any] = dict(
        mode="payment",
        line_items=line_items,
        success_url=SUCCESS_URL,
        cancel_url=CANCEL_URL,
        # Show the promo-code field on Checkout — lets us apply a discount code on
        # test runs and supports real merchant promotions. (Stripe's minimum live
        # charge is $0.50 CAD, so a code can reduce the total to $0.50, or to $0
        # for a fully-free comp; it cannot settle a real charge below $0.50.)
        allow_promotion_codes=True,
        client_reference_id=pos_order_id or order.get("merchant_id", ""),
        metadata={
            "merchant_id": order.get("merchant_id", ""),
            "pos_order_id": pos_order_id,
            "caller_phone": order.get("caller_phone", ""),
        },
    )
    if connect_account:
        pi_data: dict[str, Any] = {"transfer_data": {"destination": connect_account}}
        # Auto-take our fee at charge time: flat service fee + optional %. Stripe
        # routes this to Meridian and pays the merchant the remainder (daily).
        # Capped below the order so we never try to take more than was charged.
        fee = SERVICE_FEE_CENTS + int(round(amount * PLATFORM_FEE_BPS / 10000))
        if fee > 0:
            pi_data["application_fee_amount"] = min(fee, max(amount - 1, 0))
        kwargs["payment_intent_data"] = pi_data

    session = stripe.checkout.Session.create(**kwargs)
    # Stripe SDK objects are NOT dicts — use subscript access, not .get()
    # (.get raises AttributeError on a StripeObject).
    # Branded short link so the texted URL is "<pay base>/p/<code>" instead of
    # Stripe's ~400-char URL. Only used if we can persist the mapping; otherwise
    # the customer still gets the full (always-working) Stripe URL.
    short_code = uuid.uuid4().hex[:8]
    recorded = await _record_checkout_session(
        order, merchant_config, pos_order_id, session, amount, currency, short_code)
    url = f"{PUBLIC_PAY_BASE}/p/{short_code}" if recorded else session["url"]
    logger.info("Stripe checkout %s (%s) for merchant %s ($%.2f %s) -> %s",
                session["id"], "connect" if connect_account else "platform",
                order.get("merchant_id"), amount / 100, currency.upper(), url)
    return {"url": url, "checkout_url": session["url"], "method": "stripe",
            "link_id": session["id"], "session_id": session["id"], "short_code": short_code}


async def _record_checkout_session(order, merchant_config, pos_order_id, session, amount, currency,
                                   short_code: str = "") -> bool:
    """Persist the session so the /p/<short_code> redirect can resolve it.
    Returns True only if the row was written — the caller only hands out the
    branded short link when this succeeds (else it uses the full Stripe URL)."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
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
                    "short_code": short_code or None,
                    "caller_phone": order.get("caller_phone", ""),
                },
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                         "Content-Type": "application/json", "Prefer": "return=minimal"},
            )
        if res.status_code in (200, 201, 204):
            return True
        logger.warning("checkout_sessions insert HTTP %s: %s", res.status_code, res.text[:200])
        return False
    except Exception as e:  # noqa: BLE001 — recording is best-effort
        logger.warning("checkout_sessions insert failed: %s", e)
        return False


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

    from pos_connector import clover_api_base
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{clover_api_base()}/v3/merchants/{merchant_id}/pay_links",
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
