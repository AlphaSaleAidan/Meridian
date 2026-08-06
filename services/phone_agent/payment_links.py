"""
Payment link generator — creates checkout URLs from connected POS systems.
Square and Toast have native payment link APIs; Clover uses Hosted Checkout
via a lazily-created session behind the branded /p short link (HCO sessions
expire 15 minutes after creation, so they're created on tap, not at SMS time).
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


# ── 3-MODE FEE ALLOCATION (business_pays / split_5050 / customer_pays) ────────
#
# Rep-set at close, FIXED thereafter (stored on phone_agent_config.
# fee_allocation_mode, migration 048; owner sees it read-only and can only file
# a change request). Allocates the PER-ORDER fee between the customer's total
# and the merchant's payout. Two fee components:
#   M  Meridian's per-order fee — the merchant's effective per-order fee
#      (rep override, else the plan-tier rate). Same tier table the split model
#      uses (tier_order_fee_cents) — NEVER re-hardcoded here.
#   S  Stripe's processing fee = round(subtotal × 2.9%) + 30¢.
#   F = M + S  is fully allocated in every mode (customer surcharge + business
#      absorbed == F, always).
#
# fee_allocation_mode = None (or an unknown value) → allocate_fee returns None
# and callers fall back to the pre-existing FEE_SPLIT / gross-up behavior
# byte-for-byte. This new model only activates when a mode is explicitly set.
FEE_ALLOCATION_MODES = ("business_pays", "split_5050", "customer_pays")

# Stripe's per-charge processing rate for the S component. Independent of the
# legacy STRIPE_FEE_BPS/STRIPE_FEE_FIXED_CENTS gross-up knobs (those govern the
# old model) but defaulted to the same 2.9% + 30¢ Stripe actually charges.
MODE_STRIPE_FEE_BPS = int(os.getenv("MERIDIAN_MODE_STRIPE_FEE_BPS", "290") or 290)
MODE_STRIPE_FEE_FIXED_CENTS = int(os.getenv("MERIDIAN_MODE_STRIPE_FEE_FIXED_CENTS", "30") or 30)


def meridian_fee_cents(plan_tier: str, currency: str,
                       override_cents: int | None = None) -> int:
    """M — Meridian's per-order fee for this order: the rep-negotiated override
    when set, else the plan-tier rate (tier_order_fee_cents). This is the SAME
    per-order fee the split model surfaces; kept as a thin wrapper so the mode
    math and the split math can never diverge on M."""
    if override_cents is not None:
        try:
            return max(int(override_cents), 0)
        except (TypeError, ValueError):
            pass
    return tier_order_fee_cents(plan_tier, currency)


def stripe_fee_cents(subtotal_cents: int) -> int:
    """S — Stripe's processing fee on the order subtotal: 2.9% + 30¢."""
    return int(round(max(subtotal_cents, 0) * MODE_STRIPE_FEE_BPS / 10000)) \
        + MODE_STRIPE_FEE_FIXED_CENTS


def allocate_fee(subtotal_cents: int, plan_tier: str, currency: str,
                 mode: str | None, override_cents: int | None = None) -> dict | None:
    """Allocate the per-order fee F = M + S between customer and business for
    the given mode. Returns a dict, or None when `mode` is None/unknown (the
    caller then keeps the legacy fee behavior).

    Keys (all integer cents):
      meridian_fee_cents        M
      stripe_fee_cents          S
      total_fee_cents           F = M + S
      customer_surcharge_cents  added to the customer's total
      business_absorbed_cents   taken out of the merchant's payout
      customer_total_cents      subtotal + customer surcharge
      mode                      the resolved mode

    business_pays  customer 0,          business F
    split_5050     customer ceil(F/2),  business floor(F/2)  (ODD CENT → customer)
    customer_pays  customer F,          business 0
    """
    if mode not in FEE_ALLOCATION_MODES:
        return None
    subtotal_cents = max(int(subtotal_cents), 0)
    m = meridian_fee_cents(plan_tier, currency, override_cents)
    s = stripe_fee_cents(subtotal_cents)
    f = m + s
    if mode == "business_pays":
        customer = 0
    elif mode == "customer_pays":
        customer = f
    else:  # split_5050 — odd cent to the customer side (ceil vs floor)
        customer = (f + 1) // 2          # == ceil(f / 2)
    business = f - customer               # floor(f / 2) for the split; F or 0 otherwise
    return {
        "meridian_fee_cents": m,
        "stripe_fee_cents": s,
        "total_fee_cents": f,
        "customer_surcharge_cents": customer,
        "business_absorbed_cents": business,
        "customer_total_cents": subtotal_cents + customer,
        "mode": mode,
    }


def mode_application_fee_cents(subtotal_cents: int, alloc: dict) -> int:
    """Stripe application fee (Meridian's cut from a destination charge) under
    the 3-mode model: the WHOLE per-order fee F routes to Meridian regardless of
    who fronted which half — the customer surcharge rides the charge as a line
    item, and the business-absorbed part is deducted from the merchant payout.
    Capped below the charge total so we never take more than was charged."""
    fee = int(alloc["total_fee_cents"])
    charge_total = int(subtotal_cents) + int(alloc["customer_surcharge_cents"])
    return min(fee, max(charge_total - 1, 0))


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
    order-total line (charges the correct amount either way).

    Itemized lines bill unit_price × quantity, but the normalizer's order
    total also carries sales tax and per-item modifier charges (toppings) —
    neither has a line of its own, so itemized checkouts silently
    undercharged by that delta (the merchant ate the tax). Close the gap
    with one explicit "Tax & extras" line so the customer pays exactly the
    total the order was confirmed (and recorded in phone_orders) at."""
    items, ok = [], True
    items_cents = 0
    for i in order.get("items", []):
        price = i.get("unit_price", i.get("price"))
        if price is None:
            ok = False
            break
        name = i.get("name", "Item")
        if i.get("size"):
            name += f" ({i['size']})"
        qty = int(i.get("quantity", 1) or 1)
        unit_cents = int(round(float(price) * 100))
        items_cents += unit_cents * qty
        items.append({
            "quantity": qty,
            "price_data": {
                "currency": currency,
                "unit_amount": unit_cents,
                "product_data": {"name": name},
            },
        })
    if ok and items:
        delta = _order_amount_cents(order) - items_cents
        if delta > 0:
            items.append({
                "quantity": 1,
                "price_data": {
                    "currency": currency,
                    "unit_amount": delta,
                    "product_data": {"name": "Tax & extras"},
                },
            })
        return items
    return [{
        "quantity": 1,
        "price_data": {
            "currency": currency,
            "unit_amount": _order_amount_cents(order),
            "product_data": {"name": "Phone order"},
        },
    }]


def _clover_native_pay_enabled() -> bool:
    """Global kill-switch for the Clover-native text-to-pay rail. Read at call
    time (not import) so ops can flip it without a redeploy-order dance and
    tests can monkeypatch the env. Independent of the per-merchant
    payment_link_provider column — two gates, both default OFF."""
    return os.getenv("CLOVER_NATIVE_PAY_ENABLED", "0") == "1"


async def create_checkout(order: dict[str, Any], merchant_config, pos_order_id: str = "") -> dict:
    """Preferred checkout entry point. When unified payments are on and a Stripe
    key is configured, ALWAYS produce a real Stripe hosted-checkout link:
      • merchant onboarded for Connect → destination charge to their account
        (+ Meridian application fee);
      • not onboarded yet (demo / pre-Connect) → direct charge on Meridian's own
        platform account, so the customer can still pay now (no dead link).
    Stripe supports CAD, so this is the rail that actually works for Canada — the
    per-POS fallback below stranded CAD orders on a non-existent checkout page.
    Same return shape ({url, method, ...}) so callers/SMS are unchanged.

    CLOVER-NATIVE TEXT-TO-PAY — two INDEPENDENT gates, both default OFF:
    the global CLOVER_NATIVE_PAY_ENABLED env (kill-switch) AND the merchant's
    payment_link_provider column set to "clover". Opted-in merchants get a
    Clover Hosted Checkout link via the lazy /p short-link flow (the HCO
    session is created when the customer TAPS, because sessions expire 15
    minutes after creation) charging on the merchant's OWN Clover processing;
    Meridian's fee rides as a cart line item and is booked to the voice ledger
    on verified payment. Default is "stripe" → everything below runs
    byte-for-byte unchanged. Any failure on the Clover path falls through to
    the existing behavior so an order is never stranded."""
    provider = (getattr(merchant_config, "payment_link_provider", "") or "").strip().lower()
    if provider == "clover" and _clover_native_pay_enabled():
        try:
            if await _merchant_has_clover(merchant_config):
                return await _clover_lazy_checkout(
                    order, pos_order_id, _clover_merchant_id_hint(merchant_config),
                    plan_tier=getattr(merchant_config, "plan_tier", "") or "",
                    fee_override_cents=getattr(merchant_config, "order_fee_cents", None),
                    fee_allocation_mode=getattr(merchant_config, "fee_allocation_mode", None))
            logger.warning(
                "payment_link_provider=clover but no Clover connection for %s — "
                "falling back to default checkout", order.get("merchant_id", ""))
        except Exception as e:  # noqa: BLE001 — never strand the order; fall through
            logger.error("Clover HCO link failed, falling back to default checkout: %s", e)
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


async def _merchant_currency(merchant_id: str) -> str:
    """Charge currency for a merchant, derived from its billing terms'
    source_market ('us' → usd, else cad). Fails open to 'cad' (the historical
    default) so a merchant with no billing terms or a lookup hiccup is unchanged
    — this only fixes US merchants being charged in CAD when nothing upstream set
    an explicit order currency."""
    if not (SUPABASE_URL and SUPABASE_KEY and merchant_id):
        return "cad"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/merchant_billing_terms",
                params={
                    "merchant_id": f"eq.{merchant_id}",
                    "superseded_at": "is.null",
                    "select": "source_market",
                    "limit": "1",
                },
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            )
        if res.status_code == 200 and res.json():
            market = (res.json()[0].get("source_market") or "").strip().lower()
            if market == "us":
                return "usd"
    except Exception as e:  # noqa: BLE001 — currency resolution is best-effort
        logger.warning("merchant currency lookup failed for %s: %s", merchant_id, e)
    return "cad"


async def _stripe_checkout(
    order: dict[str, Any], merchant_config, pos_order_id: str, connect_account: str = "",
    extra_metadata: dict | None = None, success_url: str = "", cancel_url: str = "",
) -> dict:
    """Stripe hosted Checkout (POS-agnostic). With `connect_account` → a
    destination charge to that connected account + Meridian application fee.
    Without one → a direct charge on Meridian's platform account so unboarded
    merchants (and the demo) can still take payment immediately."""
    stripe = _stripe()
    # Explicit order currency wins; otherwise derive from the merchant's market
    # (US → usd) instead of blindly defaulting to CAD, which charged US merchants
    # in Canadian dollars when nothing upstream set a currency.
    currency = (order.get("currency") or await _merchant_currency(
        getattr(merchant_config, "merchant_id", "") or order.get("merchant_id", ""))).lower()
    amount = _order_amount_cents(order)

    # Customer-side per-order surcharge (fee-split model): Meridian's tier fee
    # + fixed 30¢, added to the total as its own line item. 0 when the split is
    # disabled or on demo test charges.
    surcharge = 0
    # 3-mode allocation (business_pays/split_5050/customer_pays), when the rep
    # set a fee_allocation_mode at close. Present → it wins over FEE_SPLIT_ENABLED
    # and drives BOTH the customer surcharge line and the application fee below.
    # None/unknown → falls through to the pre-existing behavior byte-for-byte.
    alloc = allocate_fee(
        amount, getattr(merchant_config, "plan_tier", "") or "", currency,
        getattr(merchant_config, "fee_allocation_mode", None),
        override_cents=getattr(merchant_config, "order_fee_cents", None))

    # Demo test-charge override → flat ~$0.50 line instead of the real total.
    if DEMO_TEST_CHARGE_CENTS and order.get("merchant_id", "") in _DEMO_MERCHANT_IDS:
        amount = max(50, DEMO_TEST_CHARGE_CENTS)  # Stripe CAD minimum is 50¢
        alloc = None  # never surcharge a demo test charge
        line_items = [{"quantity": 1, "price_data": {
            "currency": currency, "unit_amount": amount,
            "product_data": {"name": "Demo test charge"}}}]
        logger.info("DEMO test-charge override: charging %d¢ (merchant=%s)",
                    amount, order.get("merchant_id"))
    else:
        line_items = _stripe_line_items(order, currency)
        if alloc is not None:
            surcharge = alloc["customer_surcharge_cents"]
            if surcharge > 0:
                line_items.append({
                    "quantity": 1,
                    "price_data": {
                        "currency": currency,
                        "unit_amount": surcharge,
                        "product_data": {"name": "Service & processing fee"},
                    },
                })
        elif FEE_SPLIT_ENABLED:
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
        if alloc is not None:
            # 3-mode: the whole per-order fee (M + S) routes to Meridian; the
            # customer surcharge rode the charge, the rest comes from the payout.
            fee = mode_application_fee_cents(amount, alloc)
        elif FEE_SPLIT_ENABLED and surcharge:
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
            # Clover has NO payment-link API (the old POST /v3/merchants/{mid}/
            # pay_links endpoint never existed — it 405'd and silently fell back
            # here). The real rail is Hosted Checkout, created lazily behind the
            # /p short link because HCO sessions expire 15 min after creation.
            # location_id carries the Clover merchant id on this branch.
            return await _clover_lazy_checkout(order, pos_order_id, location_id)
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


# ── Clover Hosted Checkout (text-to-pay) ─────────────────────────────────────
#
# Clover's real payment-page API is Hosted Checkout:
#   POST {host}/invoicingcheckoutservice/v1/checkouts
# (the previous _clover_payment_link posted to /v3/merchants/{mid}/pay_links,
# which does not exist in Clover's API — it always errored and silently fell
# back to the Meridian checkout page).
#
# HCO sessions EXPIRE 15 MINUTES after creation, so we must NOT create one at
# SMS-send time (customers routinely tap later). Instead we persist everything
# needed in checkout_sessions (payload JSONB) and the backend /p/{code} handler
# creates the session lazily on tap — see src/api/routes/pay_redirect.py. The
# merchant's Clover access token is deliberately NOT stored in the row; the /p
# handler re-resolves it from the stored (encrypted) Clover connection.


def _split_name(full_name: str) -> tuple[str, str]:
    """HCO requires at least one of customer firstName/lastName/email.
    "Guest" when the caller gave no name (guess: docs don't cover empty)."""
    parts = (full_name or "").strip().split()
    if not parts:
        return "Guest", ""
    return parts[0], " ".join(parts[1:])


def _clover_hco_line_items(order: dict[str, Any], plan_tier: str = "",
                           fee_override_cents: int | None = None,
                           fee_allocation_mode: str | None = None) -> tuple[list[dict], int]:
    """HCO shoppingCart lineItems (unit price in CENTS) + their total.

    Hosted Checkout ignores the merchant's Clover tax configuration and
    inventory, so tax must be computed INTO the cart: itemized lines get an
    explicit "Tax" line; unpriced orders get a single tax-inclusive total line.

    Under the fee-split model — or a rep-set fee_allocation_mode — the customer
    surcharge ALSO rides as a cart line item (mirroring the Stripe rail): the
    money settles on the merchant's own Clover, and Meridian's full fee is
    booked to the voice ledger when the payment is verified server-side
    (src/services/clover_hco.settle). A set mode wins over FEE_SPLIT_ENABLED.
    """
    items, ok = [], True
    for i in order.get("items", []):
        price = i.get("unit_price", i.get("price"))
        if price is None:
            ok = False
            break
        name = i.get("name", "Item")
        if i.get("size"):
            name += f" ({i['size']})"
        line = {
            "name": name,
            "price": int(round(float(price) * 100)),
            "unitQty": int(i.get("quantity", 1) or 1),
        }
        note = (i.get("special_instructions") or "").strip()
        if note:
            line["note"] = note
        items.append(line)
    subtotal_cents = 0
    if ok and items:
        subtotal_cents = sum(li["price"] * li["unitQty"] for li in items)
        tax_cents = int(round(float(order.get("tax", 0) or 0) * 100))
        if tax_cents > 0:
            items.append({"name": "Tax", "price": tax_cents, "unitQty": 1})
            subtotal_cents += tax_cents
    else:
        # tax-inclusive single line (order total already includes tax)
        subtotal_cents = _order_amount_cents(order)
        items = [{"name": "Phone order", "price": subtotal_cents, "unitQty": 1}]
    currency = (order.get("currency") or "cad").lower()
    alloc = allocate_fee(subtotal_cents, plan_tier, currency, fee_allocation_mode,
                         override_cents=fee_override_cents)
    if alloc is not None:
        surcharge = alloc["customer_surcharge_cents"]
        if surcharge > 0:
            items.append({"name": "Service & processing fee",
                          "price": surcharge, "unitQty": 1})
    elif FEE_SPLIT_ENABLED:
        surcharge = customer_surcharge_cents(plan_tier, currency,
                                             override_cents=fee_override_cents)
        if surcharge > 0:
            items.append({"name": "Service & processing fee",
                          "price": surcharge, "unitQty": 1})
    total = sum(li["price"] * li["unitQty"] for li in items)
    return items, total


def _clover_merchant_id_hint(merchant_config) -> str:
    """Best order-time guess at the Clover merchant id. Manual configs store it
    in pos_location_id; OAuth merchants leave this empty and the /p handler
    resolves external_merchant_id from pos_connections at tap time."""
    if (getattr(merchant_config, "pos_system", "") or "") == "clover":
        return (getattr(merchant_config, "pos_location_id", "") or "").strip()
    return ""


async def _merchant_has_clover(merchant_config) -> bool:
    """Does this merchant have a usable Clover connection? Manual creds on the
    phone config win; else check for a connected pos_connections row (existence
    only — the token stays encrypted, the /p handler decrypts it at tap time)."""
    if (
        (getattr(merchant_config, "pos_system", "") or "") == "clover"
        and (getattr(merchant_config, "pos_access_token", "") or "")
        and (getattr(merchant_config, "pos_location_id", "") or "")
    ):
        return True
    merchant_id = getattr(merchant_config, "merchant_id", "") or ""
    if not (SUPABASE_URL and SUPABASE_KEY and merchant_id):
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/pos_connections",
                params={
                    "org_id": f"eq.{merchant_id}",
                    "provider": "eq.clover",
                    "status": "eq.connected",
                    "select": "id",
                    "limit": "1",
                },
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            )
        return res.status_code == 200 and bool(res.json())
    except Exception as e:  # noqa: BLE001 — connection check is best-effort
        logger.warning("Clover connection lookup failed: %s", e)
        return False


async def _clover_lazy_checkout(
    order: dict[str, Any], pos_order_id: str, clover_merchant_id: str = "",
    plan_tier: str = "", fee_override_cents: int | None = None,
    fee_allocation_mode: str | None = None,
) -> dict:
    """Write the checkout_sessions row that backs a LAZY Clover Hosted Checkout
    and return the branded short link. No Clover HTTP happens here — the /p
    handler creates the HCO session on tap (15-min expiry starts then) and this
    row carries everything it needs in `payload` (except the access token,
    which it re-resolves from the merchant's stored Clover connection).

    Raises when the row can't be persisted: a /p link that resolves to nothing
    is worse than falling back to the caller's default checkout path."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        raise RuntimeError("supabase_not_configured")

    currency = (order.get("currency") or "cad").lower()
    line_items, amount_cents = _clover_hco_line_items(order, plan_tier,
                                                      fee_override_cents,
                                                      fee_allocation_mode)
    first, last = _split_name(order.get("customer_name", ""))
    customer: dict[str, Any] = {"firstName": first}
    if last:
        customer["lastName"] = last
    if order.get("caller_phone"):
        customer["phoneNumber"] = order["caller_phone"]

    short_code = uuid.uuid4().hex[:8]
    row = {
        "merchant_id": order.get("merchant_id", ""),
        "pos_order_id": pos_order_id,
        "provider": "clover",
        "provider_ref": None,  # set by /p on first tap (HCO checkoutSessionId)
        "amount_cents": amount_cents,
        "currency": currency,
        "status": "created",
        "checkout_url": None,  # set by /p on first tap (HCO href)
        "short_code": short_code,
        "caller_phone": order.get("caller_phone", ""),
        "payload": {
            # ready-to-POST HCO body (see src/services/clover_hco.py)
            "hco_request": {
                "customer": customer,
                "shoppingCart": {"lineItems": line_items},
                # back to us after paying — /pay/clover/return verifies the
                # payment server-side (the redirect alone is never trusted)
                "redirectUrls": {
                    "success": f"{PUBLIC_PAY_BASE}/pay/clover/return/{short_code}",
                    "failure": f"{PUBLIC_PAY_BASE}/pay/cancel",
                    "cancel": f"{PUBLIC_PAY_BASE}/pay/cancel",
                },
            },
            "clover_merchant_id": clover_merchant_id or "",
            # lets settlement compute the exact tier fee for the ledger
            "plan_tier": plan_tier or "",
            # rep-negotiated per-order fee override (rep-portal fee slider);
            # None = plan-tier / env default
            "fee_override_cents": fee_override_cents,
            # rep-set fee allocation mode (business_pays/split_5050/customer_pays);
            # None = legacy fee-split / env default
            "fee_allocation_mode": fee_allocation_mode,
            # pre-surcharge subtotal (cents) so settlement reconstructs the exact
            # allocation (S depends on the subtotal, not the surcharged total).
            "subtotal_cents": _order_amount_cents(order),
        },
        # legacy meridian-checkout columns so a fallback page could render the
        # order if HCO creation fails at tap time
        "customer_name": order.get("customer_name", ""),
        "customer_phone": order.get("caller_phone", ""),
        "order_type": order.get("order_type", "pickup"),
        "items": order.get("items", []),
        "subtotal": order.get("subtotal", 0),
        "tax": order.get("tax", 0),
        "total": order.get("total", 0),
        "pos_system": "clover",
        "source": "phone_agent",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.post(
            f"{SUPABASE_URL}/rest/v1/checkout_sessions",
            json=row,
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                     "Content-Type": "application/json", "Prefer": "return=minimal"},
        )
    if res.status_code not in (200, 201, 204):
        logger.warning("clover checkout_sessions insert HTTP %s: %s",
                       res.status_code, res.text[:200])
        raise RuntimeError(f"checkout_sessions_insert_{res.status_code}")

    url = f"{PUBLIC_PAY_BASE}/p/{short_code}"
    logger.info("Clover HCO lazy link for merchant %s ($%.2f %s) -> %s",
                order.get("merchant_id"), amount_cents / 100, currency.upper(), url)
    return {"url": url, "method": "clover", "link_id": short_code, "short_code": short_code}


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
