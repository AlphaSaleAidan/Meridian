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
# Stripe-processing gross-up ("Case B"): destination charges debit Stripe's
# processing fee from the PLATFORM balance, not the merchant's — verified
# empirically in test mode (app fee $0.50 on a $32 order → Meridian nets
# −$0.73; grossed-up fee → Meridian nets exactly +$0.50). Adding the estimated
# processing cost to the application fee deducts it from the merchant's payout
# in transit, so the merchant bears card fees exactly like on their own POS.
# Rates are env-tunable because Stripe's actual fee varies by card/country
# (Amex/international run higher); the residual is pennies either way.
STRIPE_GROSSUP_ENABLED = os.getenv("STRIPE_FEE_GROSSUP_ENABLED", "1") == "1"
STRIPE_FEE_BPS = int(os.getenv("STRIPE_FEE_BPS", "290") or 290)          # 2.9%
STRIPE_FEE_FIXED_CENTS = int(os.getenv("STRIPE_FEE_FIXED_CENTS", "30") or 30)


def application_fee_cents(amount_cents: int, service_fee_cents: int | None = None) -> int:
    """Total application fee on a destination charge of `amount_cents`:
    Meridian's service fee + optional bps + (when grossed up) Stripe's
    estimated processing cost. Always capped below the charge amount.
    `service_fee_cents` is the per-merchant override (rep fee slider,
    phone_agent_config.order_fee_cents); None = the env default."""
    base = SERVICE_FEE_CENTS if service_fee_cents is None else int(service_fee_cents)
    fee = base + int(round(amount_cents * PLATFORM_FEE_BPS / 10000))
    if STRIPE_GROSSUP_ENABLED:
        fee += int(round(amount_cents * STRIPE_FEE_BPS / 10000)) + STRIPE_FEE_FIXED_CENTS
    return min(fee, max(amount_cents - 1, 0))


# FEE SPLIT (three-tier pricing model): when enabled, per-order economics move
# from "merchant bears everything in transit" (Case B gross-up above) to a
# customer/merchant split:
#   • CUSTOMER pays: order subtotal + Meridian's per-order fee (by the
#     merchant's plan tier) + Stripe's fixed 30¢ — added to checkout as its
#     own "Service & processing fee" line item.
#   • MERCHANT bears: MERCHANT_FEE_BPS (2.99%) of the order subtotal,
#     deducted from their payout via the application fee.
# The application fee routes surcharge + 2.99% to Meridian's balance; Stripe
# debits its actual processing (2.9% + 30¢ of the grossed-up total) from the
# platform, netting Meridian ≈ the tier's per-order fee on every order.
# Default OFF: live behavior is byte-for-byte the gross-up model until the
# flag is set.
FEE_SPLIT_ENABLED = os.getenv("MERIDIAN_FEE_SPLIT_ENABLED", "0") == "1"
MERCHANT_FEE_BPS = int(os.getenv("MERIDIAN_MERCHANT_FEE_BPS", "299") or 299)  # 2.99%
CUSTOMER_FIXED_FEE_CENTS = int(os.getenv("MERIDIAN_CUSTOMER_FIXED_FEE_CENTS", "30") or 30)
# Per-order Meridian fee in cents, by plan tier and charge currency:
#   Standard — no phone agent, no per-order fee
#   Premium  — US$1.49 / CA$1.99 per order
#   Command  — US$1.00 / CA$1.39 per order
TIER_ORDER_FEE_CENTS: dict[str, dict[str, int]] = {
    "usd": {"standard": 0, "premium": 149, "command": 100},
    "cad": {"standard": 0, "premium": 199, "command": 139},
}
# Merchants with no/unknown plan_tier bill at this tier's per-order rate.
DEFAULT_ORDER_FEE_TIER = os.getenv("MERIDIAN_DEFAULT_ORDER_FEE_TIER", "premium")


def tier_order_fee_cents(plan_tier: str, currency: str) -> int:
    """Meridian's per-order fee for a merchant's plan tier, in the charge currency."""
    fees = TIER_ORDER_FEE_CENTS.get((currency or "cad").lower(), TIER_ORDER_FEE_CENTS["cad"])
    tier = (plan_tier or "").strip().lower()
    if tier not in fees:
        tier = DEFAULT_ORDER_FEE_TIER
    return fees.get(tier, 0)


def customer_surcharge_cents(plan_tier: str, currency: str,
                             override_cents: int | None = None) -> int:
    """Customer-side per-order surcharge: Meridian's per-order fee + the fixed
    30¢. `override_cents` is the rep-negotiated per-merchant fee
    (phone_agent_config.order_fee_cents); None = the plan-tier rate."""
    fee = (int(override_cents) if override_cents is not None
           else tier_order_fee_cents(plan_tier, currency))
    return max(fee, 0) + CUSTOMER_FIXED_FEE_CENTS


def merchant_order_fee_cents(merchant_config, currency: str) -> int:
    """Meridian's per-order fee for THIS merchant: the per-merchant override
    when set, else the plan-tier default. One rule for every rail (Stripe
    split/legacy, Clover-native, ledger credits)."""
    override = getattr(merchant_config, "order_fee_cents", None)
    if override is not None:
        try:
            return max(int(override), 0)
        except (TypeError, ValueError):
            pass
    return tier_order_fee_cents(getattr(merchant_config, "plan_tier", "") or "", currency)


def split_application_fee_cents(subtotal_cents: int, surcharge_cents: int) -> int:
    """Application fee under the split model: the customer-paid surcharge plus
    the merchant-side percentage of the order subtotal, capped below the total
    charge (subtotal + surcharge) so we never take more than was charged."""
    fee = surcharge_cents + int(round(subtotal_cents * MERCHANT_FEE_BPS / 10000))
    total = subtotal_cents + surcharge_cents
    return min(fee, max(total - 1, 0))


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


# Native Clover pay-by-text rail. Two INDEPENDENT gates, both default OFF:
# this global env AND the merchant's phone_agent_config.native_pos_pay column.
CLOVER_NATIVE_PAY_ENABLED = os.getenv("CLOVER_NATIVE_PAY_ENABLED", "0") == "1"


def _clover_hco_base() -> str:
    """Clover Hosted Checkout host — same CLOVER_ENVIRONMENT contract as the
    order-writing connectors."""
    if os.getenv("CLOVER_ENVIRONMENT", "").strip().lower() == "sandbox":
        return "https://apisandbox.dev.clover.com"
    return "https://www.clover.com"


async def _clover_hosted_checkout(order: dict[str, Any], merchant_config, pos_order_id: str) -> dict:
    """Clover Hosted Checkout — pay-by-text on the merchant's OWN Clover
    processing (money settles like their in-store card sales; never touches
    Meridian's Stripe). Meridian's fee still applies: under the fee split the
    customer surcharge rides as a checkout line item, and the full fee is
    booked to the voice ledger when the payment is server-side verified at
    /pay/clover/return (the redirect alone is never trusted).

    POST {host}/invoicingcheckoutservice/v1/checkouts with X-Clover-Merchant-Id;
    the response href is Clover's hosted pay page."""
    token = (getattr(merchant_config, "pos_access_token", "") or "").strip()
    clover_mid = (getattr(merchant_config, "pos_location_id", "") or "").strip()
    if not (token and clover_mid):
        raise RuntimeError("clover_native_missing_credentials")

    currency = (order.get("currency") or "cad").lower()
    short_code = uuid.uuid4().hex[:8]

    line_items = []
    for i in order.get("items", []):
        price = i.get("unit_price", i.get("price", 0)) or 0
        name = i.get("name", "Item")
        if i.get("size"):
            name += f" ({i['size']})"
        line_items.append({
            "name": name[:127],
            "unitQty": int(i.get("quantity", 1) or 1),
            "price": int(round(float(price) * 100)),
        })
    if not line_items:
        line_items = [{"name": "Phone order", "unitQty": 1,
                       "price": _order_amount_cents(order)}]

    if FEE_SPLIT_ENABLED:
        surcharge = customer_surcharge_cents(
            getattr(merchant_config, "plan_tier", ""), currency,
            override_cents=getattr(merchant_config, "order_fee_cents", None))
        if surcharge > 0:
            line_items.append({"name": "Service & processing fee",
                               "unitQty": 1, "price": surcharge})

    amount_total = sum(li["price"] * li["unitQty"] for li in line_items)

    name_parts = (order.get("customer_name") or "").strip().split(" ", 1)
    customer: dict[str, Any] = {
        "firstName": (name_parts[0] if name_parts else "") or "Phone",
        "lastName": (name_parts[1] if len(name_parts) > 1 else "") or "Order",
    }
    if order.get("caller_phone"):
        customer["phoneNumber"] = order["caller_phone"]

    payload = {
        "customer": customer,
        "shoppingCart": {"lineItems": line_items},
        "redirectUrls": {
            "success": f"{PUBLIC_PAY_BASE}/pay/clover/return/{short_code}",
            "failure": f"{PUBLIC_PAY_BASE}/pay/cancel",
            "cancel": f"{PUBLIC_PAY_BASE}/pay/cancel",
        },
    }

    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            f"{_clover_hco_base()}/invoicingcheckoutservice/v1/checkouts",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Clover-Merchant-Id": clover_mid,
                "Content-Type": "application/json",
            },
        )
    if res.status_code not in (200, 201):
        raise RuntimeError(f"clover_hco_http_{res.status_code}: {res.text[:200]}")
    data = res.json() or {}
    href = data.get("href") or data.get("checkoutPageUrl") or ""
    session_id = data.get("checkoutSessionId") or data.get("id") or ""
    if not href:
        raise RuntimeError("clover_hco_no_href")

    recorded = await _record_checkout_session(
        order, merchant_config, pos_order_id,
        {"id": session_id, "url": href}, amount_total, currency, short_code,
        provider="clover_hco",
    )
    url = f"{PUBLIC_PAY_BASE}/p/{short_code}" if recorded else href
    logger.info("Clover hosted checkout %s for merchant %s ($%.2f %s) -> %s",
                session_id, order.get("merchant_id"), amount_total / 100,
                currency.upper(), url)
    return {"url": url, "checkout_url": href, "method": "clover_native",
            "link_id": session_id, "session_id": session_id,
            "short_code": short_code}


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
    # Native Clover rail first when BOTH gates are on and this is a Clover
    # merchant with credentials — any failure falls straight through to Stripe
    # so a broken native link never strands the order.
    if (CLOVER_NATIVE_PAY_ENABLED
            and getattr(merchant_config, "native_pos_pay", False)
            and (getattr(merchant_config, "pos_system", "") or "").strip().lower() == "clover"):
        try:
            return await _clover_hosted_checkout(order, merchant_config, pos_order_id)
        except Exception as e:  # noqa: BLE001 — Stripe rail is the safety net
            logger.warning("Clover native checkout failed, using Stripe rail: %s", e)

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


async def create_website_checkout(
    order: dict[str, Any],
    merchant_config,
    website_order_id: str,
    success_url: str = "",
    cancel_url: str = "",
) -> dict:
    """Stripe-ONLY checkout for website/mobile orders. Unlike create_checkout
    there is no per-POS payment-link fallback: mobile orders must be paid
    through Stripe before the kitchen sees them, so this raises instead of
    degrading. The session carries website_order_id in metadata — the Connect
    webhook uses it to mark the order paid and release the kitchen ticket."""
    if not (UNIFIED_PAYMENTS_ENABLED and STRIPE_SECRET_KEY):
        raise RuntimeError("stripe_not_configured")
    acct = getattr(merchant_config, "stripe_account_id", "")
    charges_ok = getattr(merchant_config, "stripe_charges_enabled", False)
    connect_account = acct if (acct and charges_ok) else ""
    return await _stripe_checkout(
        order, merchant_config, "", connect_account,
        extra_metadata={"website_order_id": website_order_id},
        success_url=success_url, cancel_url=cancel_url,
    )


async def _stripe_checkout(
    order: dict[str, Any], merchant_config, pos_order_id: str, connect_account: str = "",
    extra_metadata: dict | None = None, success_url: str = "", cancel_url: str = "",
) -> dict:
    """Stripe hosted Checkout (POS-agnostic). With `connect_account` → a
    destination charge to that connected account + Meridian application fee.
    Without one → a direct charge on Meridian's platform account so unboarded
    merchants (and the demo) can still take payment immediately."""
    stripe = _stripe()
    currency = (order.get("currency") or "cad").lower()
    amount = _order_amount_cents(order)

    # Customer-side per-order surcharge (fee-split model): Meridian's tier fee
    # + fixed 30¢, added to the total as its own line item. 0 when the split is
    # disabled or on demo test charges.
    surcharge = 0

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
        if FEE_SPLIT_ENABLED:
            surcharge = customer_surcharge_cents(
                getattr(merchant_config, "plan_tier", ""), currency,
                override_cents=getattr(merchant_config, "order_fee_cents", None))
            if surcharge > 0:
                line_items.append({
                    "quantity": 1,
                    "price_data": {
                        "currency": currency,
                        "unit_amount": surcharge,
                        "product_data": {"name": "Service & processing fee"},
                    },
                })

    kwargs: dict[str, Any] = dict(
        mode="payment",
        line_items=line_items,
        success_url=success_url or SUCCESS_URL,
        cancel_url=cancel_url or CANCEL_URL,
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
            **(extra_metadata or {}),
        },
    )
    if connect_account:
        pi_data: dict[str, Any] = {"transfer_data": {"destination": connect_account}}
        # Auto-take our fee at charge time. Split model: the customer-paid
        # surcharge + 2.99% of the subtotal (merchant-side). Legacy model:
        # flat service fee + optional % + (Case B) Stripe gross-up. Stripe
        # routes the fee to Meridian and pays the merchant the remainder
        # (daily). Capped below the charge so we never take more than was paid.
        if FEE_SPLIT_ENABLED and surcharge:
            fee = split_application_fee_cents(amount, surcharge)
        else:
            fee = application_fee_cents(
                amount,
                service_fee_cents=getattr(merchant_config, "order_fee_cents", None))
        if fee > 0:
            pi_data["application_fee_amount"] = fee
        kwargs["payment_intent_data"] = pi_data

    session = stripe.checkout.Session.create(**kwargs)
    # Stripe SDK objects are NOT dicts — use subscript access, not .get()
    # (.get raises AttributeError on a StripeObject).
    # Branded short link so the texted URL is "<pay base>/p/<code>" instead of
    # Stripe's ~400-char URL. Only used if we can persist the mapping; otherwise
    # the customer still gets the full (always-working) Stripe URL.
    short_code = uuid.uuid4().hex[:8]
    charge_total = amount + surcharge
    recorded = await _record_checkout_session(
        order, merchant_config, pos_order_id, session, charge_total, currency, short_code)
    url = f"{PUBLIC_PAY_BASE}/p/{short_code}" if recorded else session["url"]
    logger.info("Stripe checkout %s (%s) for merchant %s ($%.2f %s, surcharge %d¢) -> %s",
                session["id"], "connect" if connect_account else "platform",
                order.get("merchant_id"), charge_total / 100, currency.upper(), surcharge, url)
    return {"url": url, "checkout_url": session["url"], "method": "stripe",
            "link_id": session["id"], "session_id": session["id"], "short_code": short_code}


async def _record_checkout_session(order, merchant_config, pos_order_id, session, amount, currency,
                                   short_code: str = "", provider: str = "stripe") -> bool:
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
                    "provider": provider,
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
                "currency": order.get("currency", "usd"),
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
                        "currency": order.get("currency", "usd"),
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
