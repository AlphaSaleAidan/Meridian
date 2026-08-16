"""
Merchant configuration loader.
Pulls merchant settings from Supabase for phone agent behavior.
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger("meridian.phone_agent.config")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# phone_agent_config is service-role-only under RLS (the anon role has no
# SELECT grant), so reads must use the service key — anon-only made every
# merchant lookup fail and silently served the demo fallback config on live
# calls. Same key selection as payment_links.py / pay_on_phone.py.
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.getenv("SUPABASE_SERVICE_KEY", "")
    or os.getenv("SUPABASE_ANON_KEY", "")
)

# ONE shared httpx client for every Supabase read in this module (lazy — created
# on first use, recreated if closed or if the running event loop changed, e.g.
# per-test asyncio.run loops). The old per-call `async with httpx.AsyncClient()`
# paid a fresh TCP+TLS handshake on every query, which is pure dead air on the
# assistant-request hot path (the caller is listening to silence until the
# agent greets). httpx.AsyncClient is safe for concurrent use; error handling
# stays with the callers exactly as before.
_http_client = None
_http_client_loop = None


def _get_http_client():
    global _http_client, _http_client_loop
    loop = asyncio.get_running_loop()
    if _http_client is None or _http_client.is_closed or _http_client_loop is not loop:
        import httpx

        _http_client = httpx.AsyncClient()
        _http_client_loop = loop
    return _http_client


# ── Short-TTL config cache ──────────────────────────────────────────────────
# A single phone call resolves the merchant config several times across its
# lifetime: assistant-request → each submit_order tool-call → end-of-call
# report → deferred POS push at payment. Each was a separate Supabase round
# trip, adding latency the caller hears (esp. before submit_order confirms) and
# load on the service-role rail. The config is read-mostly and a merchant edit
# only needs to land within a few seconds, so cache successful lookups for a
# short window. Misses/errors are NOT cached, so a just-activated merchant
# appears on the next call rather than after the TTL. Set the TTL env to 0 to
# disable entirely (revert knob).
_CONFIG_CACHE_TTL_SEC = float(os.getenv("MERIDIAN_CONFIG_CACHE_TTL_SEC", "60") or 0)
_config_cache: dict[str, tuple[float, object]] = {}


def _cache_get(key: str):
    if _CONFIG_CACHE_TTL_SEC <= 0:
        return None
    hit = _config_cache.get(key)
    if hit is None:
        return None
    ts, val = hit
    if (time.monotonic() - ts) > _CONFIG_CACHE_TTL_SEC:
        _config_cache.pop(key, None)
        return None
    return val


def _cache_put(key: str, val) -> None:
    # Only cache real hits — never None — so misconfigured/just-activated
    # merchants re-resolve immediately instead of being pinned to the miss.
    if _CONFIG_CACHE_TTL_SEC > 0 and val is not None:
        _config_cache[key] = (time.monotonic(), val)


def invalidate_config_cache(merchant_id: str = "") -> None:
    """Drop cached entries. Called with a merchant_id after a config write, or
    with no arg to clear everything (tests)."""
    if not merchant_id:
        _config_cache.clear()
        return
    _config_cache.pop(f"cfg:{merchant_id}", None)


@dataclass
class MerchantPhoneConfig:
    merchant_id: str
    business_name: str
    business_type: str
    phone_number: str
    greeting: str
    voice: str
    language: str
    active: bool
    menu_items: list[dict]
    pos_system: str
    pos_access_token: str
    pos_location_id: str
    business_hours: dict
    after_hours_message: str
    max_concurrent_calls: int
    order_types: list[str]
    special_instructions_enabled: bool
    transfer_number: str
    pos_webhook_url: str
    sms_checkout_enabled: bool
    sms_ordering_enabled: bool
    tax_rate: float = 0.13
    # Merchant-customized Text-to-Pay SMS body ({name} {business} {total}
    # {link} placeholders, safe-replaced by sms_checkout). "" = default copy.
    sms_pay_template: str = ""
    reservation_config: dict | None = None
    # BOOKINGS (migrations/081_bookings.sql). "off" (default) keeps the legacy
    # behaviour byte-for-byte: reservations are a prompt instruction, not a
    # system. "native" turns on the real availability engine and the booking
    # tools. "external_link" TEXTS the caller the merchant's own booking link
    # (migrations/083 — it used to read the URL aloud). "provider" books
    # through the merchant's own tool.
    booking_mode: str = "off"
    # Where external_link mode sends people. Falls back to the older
    # reservation_config.website_url when unset (src/services/booking_links.py).
    booking_link_url: str = ""
    # The noun the agent says out loud — "table", "chair", "bay". A barbershop
    # caller should never be offered a table.
    booking_noun: str = "reservation"
    # CANCELLATION RECOVERY (migrations/082). Off by default: texting a guest
    # that a table opened is an outbound message sent on the merchant's behalf,
    # which is theirs to opt into.
    waitlist_enabled: bool = False
    waitlist_offer_minutes: int = 15
    # Agent personality (formality/upsell/humor/custom phrases/brand keywords)
    # set in Phone Orders settings; rendered into the live system prompt.
    personality: dict | None = None
    # PAY ON THE PHONE: pay_now (DEFAULT, anti-scam — kitchen only sees PAID
    # tickets), pay_at_pickup (legacy OPEN/unpaid), or optional (caller chooses).
    payment_mode: str = "pay_now"
    # IANA tz (e.g. "America/Toronto") used to evaluate business_hours. The
    # after-hours gate only enforces when BOTH business_hours and this are set,
    # so merchants without a timezone are never mis-gated.
    business_timezone: str = ""
    # UNIFIED PAYMENTS (Stripe Connect): the merchant's connected-account id and
    # whether Stripe says it can take charges. When both are set (+ the flag),
    # checkout goes through Stripe regardless of which POS the merchant runs.
    stripe_account_id: str = ""
    stripe_charges_enabled: bool = False
    # When true, create_pos_order returns logs-only regardless of token
    # state. Demo / test merchants set this to keep live POS calls off
    # the demo path even after the merchant completes Square OAuth.
    demo_safe: bool = False
    # Subscription plan tier (standard | premium | command) — drives the
    # per-order Meridian fee under the fee-split model. "" = unset → the
    # default tier's rate applies (payment_links.DEFAULT_ORDER_FEE_TIER).
    plan_tier: str = ""
    # TEXT-TO-PAY PROVIDER: which rail generates the texted payment link.
    #   "stripe" (DEFAULT) — current behavior, byte-for-byte unchanged.
    #   "clover"          — Clover Hosted Checkout via the lazy /p short link.
    # HCO sessions expire 15 minutes after creation, so the Clover session is
    # created when the customer TAPS the link (backend /p/{code} handler), not
    # at SMS-send time. Unknown/missing values normalize to "stripe".
    payment_link_provider: str = "stripe"
    # Per-merchant signing secret for the Clover Hosted Checkout payment
    # webhook (merchant pastes our URL in Clover dashboard → Settings →
    # Ecommerce → Hosted Checkout, and copies the generated secret to us).
    # Empty = webhook rejected 401 for this merchant (fail closed).
    clover_hco_webhook_secret: str = ""
    # PER-RESTAURANT PERSONALIZATION BRIEF ──────────────────────────────
    # Generated on demand via POST /api/phone/build-brief/{merchant_id}.
    # Injected into the system prompt for tone/warmth only — the MENU is
    # still the single source of truth for items and prices.
    # Empty string = no brief = prompt is byte-for-byte unchanged (no regression).
    website_url: str = ""
    restaurant_brief: str = ""
    # OWNER SELLING NOTES (migration 074): the owner's own upsell instincts in
    # their words ("push the lamb special Fridays", "never upsell dessert at
    # lunch"). Injected as a HOW THE OWNER SELLS style block; empty = prompt
    # byte-for-byte unchanged.
    owner_selling_notes: str = ""
    # Rep-negotiated per-order Meridian fee override in cents of the charge
    # currency (rep-portal fee slider). None = plan-tier / env default.
    order_fee_cents: Optional[int] = None
    # Rep-set fee allocation mode (business_pays | split_5050 | customer_pays),
    # FIXED at close (migration 048). None = legacy fee-split / env default.
    fee_allocation_mode: Optional[str] = None
    # Voice accent group picked in the setup wizard (north_american | indian |
    # east_asian). Presentation-level grouping; `voice` carries the voice id.
    accent: str = ""
    # Per-merchant hard call cap (minutes). None = use the env default
    # (MERIDIAN_VOICE_MAX_CALL_MIN); 0 = explicitly uncapped. Threaded through
    # maxDurationSeconds, the spoken pacing line, AND the end-of-call overage
    # clamp by vapi_webhook._effective_cap_min.
    max_call_minutes: Optional[int] = None
    # The merchant's real store line (the number they forward FROM) — used by
    # the forwarding verification flow (POST /api/phone/forwarding/verify-start).
    business_line_number: str = ""
    # DELIVERY FAN-OUT: per-merchant channel toggles, e.g.
    # {"pos": true, "customer_sms": true, "merchant_sms": false}. None/missing
    # keys default to enabled (see delivery_channels.resolve_channels).
    delivery_channels: dict | None = None
    # MENU STORE (migration 20260716_menu_store): when the merchant has rows in
    # the normalized menu_items table, `menu_items` above is served from the
    # store's published/non-sold-out projection and these fields activate:
    #   sold_out_items  — published-but-sold-out names; rendered as a SOLD OUT
    #                     section in the prompt (excluded from the menu proper).
    #   menu_public_url — hosted public menu page (merchant_menus.public_slug,
    #                     https://meridian.tips/m/{slug}) mentioned by the agent.
    # None/"" (no store rows) → JSONB fallback, prompt byte-for-byte unchanged.
    sold_out_items: Optional[list] = None
    menu_public_url: str = ""
    # SCRIPT PACK (migration 20260717_phone_script_pack): named, versioned
    # call-script variant composed by services/phone_agent/script_packs.py.
    # ""/NULL/"legacy"/unknown → the untouched generic prompt, byte-for-byte
    # (vapi_webhook._resolve_script_pack is strictly fail-legacy).
    #
    # CHANGED 2026-08-16: this used to read "NEVER auto-derived from
    # business_type — packs are opt-in per merchant", and the result was
    # twelve packs written and zero merchants on one. An explicit choice here
    # still wins; when there is none, the merchant's TRADE selects the pack —
    # but ONLY a pack that has out-scored the legacy control on the bench
    # (script_packs.auto_pack_for_trade enforces that). An unproven pack is
    # never pointed at a live call automatically.
    script_pack: str = ""
    # "PAY WITH CASH" (migration 047): when True, the phone agent offers cash as
    # a payment option and cash orders reach the kitchen flagged UNPAID / CASH ON
    # PICKUP with NO payment link. False/NULL (default) = never offer cash, so
    # the prompt + dispatch path are byte-for-byte unchanged for every merchant
    # that hasn't opted in behind the warning modal.
    accept_cash: bool = False

    # Per-location voice self-funding floor (cents, may be negative = grace
    # float). When the merchant's voice_ledger balance <= this, incoming calls
    # fall back to the cheaper Telnyx rail. None = use the global env default
    # (VOICE_BALANCE_FLOOR_CENTS). Migration 072.
    voice_balance_floor_cents: Optional[int] = None


_VALID_PAYMENT_MODES = ("pay_now", "pay_at_pickup", "optional")

_VALID_PAYMENT_LINK_PROVIDERS = ("stripe", "clover")


def _norm_payment_mode(value: Optional[str]) -> str:
    """Normalize the configured payment_mode; unknown/missing → pay_now (default)."""
    mode = (value or "").strip().lower()
    return mode if mode in _VALID_PAYMENT_MODES else "pay_now"


_VALID_BOOKING_MODES = ("off", "native", "external_link", "provider")


def _norm_booking_mode(value: Optional[str]) -> str:
    """Normalize booking_mode; unknown/missing → off.

    Failing to "off" is the whole safety property: a merchant whose column is
    missing, null or garbage keeps the pre-booking prompt exactly as it was
    and the agent never offers a time it cannot honour.
    """
    mode = (value or "").strip().lower()
    return mode if mode in _VALID_BOOKING_MODES else "off"


def _norm_payment_link_provider(value: Optional[str]) -> str:
    """Normalize payment_link_provider; unknown/missing → stripe (default,
    zero behavior change for existing merchants)."""
    provider = (value or "").strip().lower()
    return provider if provider in _VALID_PAYMENT_LINK_PROVIDERS else "stripe"


_VALID_FEE_ALLOCATION_MODES = ("business_pays", "split_5050", "customer_pays")


def _norm_fee_allocation_mode(value: Optional[str]) -> Optional[str]:
    """Normalize fee_allocation_mode; unknown/missing → None (legacy behavior:
    the caller keeps the existing fee-split / env-default fee handling)."""
    mode = (value or "").strip().lower()
    return mode if mode in _VALID_FEE_ALLOCATION_MODES else None


# Base URL for the hosted public menu page (/m/{slug}).
PUBLIC_MENU_BASE = os.getenv("PUBLIC_SITE_BASE", "https://meridian.tips").rstrip("/")


def _store_row_to_agent_item(row: dict) -> dict:
    """menu_items store row (integer CENTS) → the legacy agent dict shape
    (dollars) that _system_prompt / order_normalizer consume.

    Dependency-free twin of src/services/menu_store.to_agent_shape — this
    module is imported standalone (sys.path) by vapi_webhook and must not
    import src.*. Keep the two in lockstep; tests/test_menu_agent_path.py
    asserts byte-for-byte parity.
    """
    def dollars(cents):
        return round(cents / 100, 2) if isinstance(cents, (int, float)) and cents else None

    item: dict = {"name": row.get("name") or "item"}
    price = dollars(row.get("price_cents"))
    if price is not None:
        item["price"] = price
    if row.get("category"):
        item["category"] = row["category"]
    if row.get("description"):
        item["description"] = row["description"]
    sizes = row.get("sizes")
    if isinstance(sizes, list) and sizes:
        item["sizes"] = list(sizes)
    size_prices = row.get("size_prices")
    if isinstance(size_prices, dict) and size_prices:
        converted = {}
        for size, cents in size_prices.items():
            d = dollars(cents if isinstance(cents, (int, float)) else None)
            if d is not None:
                converted[str(size)] = d
        if converted:
            item["size_prices"] = converted
            item.setdefault("sizes", list(converted.keys()))
    topping = dollars(row.get("topping_price_cents"))
    if topping is not None:
        item["topping_price"] = topping
    mods = row.get("modifications")
    if isinstance(mods, list) and mods:
        item["modifications"] = list(mods)
    return item


def _store_rows_to_menu(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Published store rows → (available agent-shape items, sold-out names).

    Sold-out items are EXCLUDED from the orderable menu (the mirror does the
    same, so legacy readers never offer them) but their names are returned so
    the prompt can tell the agent the item exists and is sold out if asked.
    """
    ordered = sorted(rows or [], key=lambda r: (
        r.get("position") is None, r.get("position") or 0,
        (r.get("name") or "").lower()))
    items: list[dict] = []
    sold_out: list[str] = []
    seen: set = set()
    for row in ordered:
        if not row.get("published"):
            continue
        name = (row.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        if row.get("sold_out"):
            sold_out.append(name)
        else:
            items.append(_store_row_to_agent_item(row))
    return items, sold_out


async def get_merchant_config(merchant_id: str) -> Optional[MerchantPhoneConfig]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("No Supabase configured — using demo config for %s", merchant_id)
        return _demo_config(merchant_id)

    cached = _cache_get(f"cfg:{merchant_id}")
    if cached is not None:
        return cached

    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        client = _get_http_client()
        res = await client.get(
            f"{SUPABASE_URL}/rest/v1/phone_agent_config",
            params={"merchant_id": f"eq.{merchant_id}", "select": "*"},
            headers=headers,
        )
        if res.status_code != 200 or not res.json():
            logger.warning("No phone config for merchant %s", merchant_id)
            return None

        row = res.json()[0]
        config = MerchantPhoneConfig(
            merchant_id=row["merchant_id"],
            business_name=row.get("business_name", ""),
            business_type=row.get("business_type", "restaurant"),
            phone_number=row.get("phone_number", ""),
            greeting=row.get("greeting", ""),
            voice=row.get("voice", "af_bella"),
            language=row.get("language", "en"),
            active=row.get("active", False),
            menu_items=row.get("menu_items", []),
            pos_system=row.get("pos_system", ""),
            pos_access_token=row.get("pos_access_token", ""),
            pos_location_id=row.get("pos_location_id", ""),
            business_hours=row.get("business_hours", {}),
            after_hours_message=row.get("after_hours_message", ""),
            max_concurrent_calls=row.get("max_concurrent_calls", 5),
            order_types=row.get("order_types", ["pickup", "delivery"]),
            special_instructions_enabled=row.get("special_instructions_enabled", True),
            transfer_number=row.get("transfer_number", ""),
            pos_webhook_url=row.get("pos_webhook_url", ""),
            sms_checkout_enabled=row.get("sms_checkout_enabled", True),
            sms_ordering_enabled=row.get("sms_ordering_enabled", True),
            tax_rate=row.get("tax_rate", 0.13),
            sms_pay_template=(row.get("sms_pay_template") or "").strip(),
            reservation_config=row.get("reservation_config") or None,
            booking_mode=_norm_booking_mode(row.get("booking_mode")),
            booking_link_url=(row.get("booking_link_url") or "").strip(),
            booking_noun=(row.get("booking_noun") or "reservation").strip() or "reservation",
            waitlist_enabled=bool(row.get("waitlist_enabled")),
            waitlist_offer_minutes=int(row.get("waitlist_offer_minutes") or 15),
            personality=row.get("personality") or None,
            # Default to pay_now if the column is missing/null (anti-scam default).
            payment_mode=_norm_payment_mode(row.get("payment_mode")),
            business_timezone=(row.get("business_timezone") or "").strip(),
            stripe_account_id=(row.get("stripe_account_id") or "").strip(),
            stripe_charges_enabled=bool(row.get("stripe_charges_enabled")),
            demo_safe=bool(row.get("demo_safe", False)),
            plan_tier=(row.get("plan_tier") or "").strip().lower(),
            payment_link_provider=_norm_payment_link_provider(
                row.get("payment_link_provider")),
            clover_hco_webhook_secret=(
                row.get("clover_hco_webhook_secret") or "").strip(),
            website_url=(row.get("website_url") or "").strip(),
            restaurant_brief=(row.get("restaurant_brief") or "").strip(),
            owner_selling_notes=(row.get("owner_selling_notes") or "").strip(),
            order_fee_cents=(int(row["order_fee_cents"])
                             if row.get("order_fee_cents") is not None else None),
            fee_allocation_mode=_norm_fee_allocation_mode(
                row.get("fee_allocation_mode")),
            accent=(row.get("accent") or "").strip().lower(),
            max_call_minutes=(int(row["max_call_minutes"])
                              if row.get("max_call_minutes") is not None else None),
            business_line_number=(row.get("business_line_number") or "").strip(),
            delivery_channels=(row.get("delivery_channels")
                               if isinstance(row.get("delivery_channels"), dict)
                               else None),
            script_pack=(row.get("script_pack") or "").strip().lower(),
            accept_cash=bool(row.get("accept_cash", False)),
            voice_balance_floor_cents=(int(row["voice_balance_floor_cents"])
                                       if row.get("voice_balance_floor_cents") is not None else None),
        )
        # MENU STORE (single source of truth): merchants with rows in the
        # normalized menu_items table get their menu from the store —
        # sold-out-aware and always current. Merchants without store rows
        # (or if the table doesn't exist yet / the read fails) keep the
        # JSONB menu loaded above — zero-migration safety, and the JSONB
        # is a write-through mirror of the store anyway (menu_store.py).
        # The two reads are independent → issued CONCURRENTLY (one round-trip
        # of latency instead of two on the assistant-request hot path).
        try:
            menu_res, menus_res = await asyncio.gather(
                client.get(
                    f"{SUPABASE_URL}/rest/v1/menu_items",
                    params={"merchant_id": f"eq.{merchant_id}",
                            "published": "is.true", "select": "*", "limit": "1000"},
                    headers=headers,
                ),
                client.get(
                    f"{SUPABASE_URL}/rest/v1/merchant_menus",
                    params={"merchant_id": f"eq.{merchant_id}",
                            "published": "is.true", "select": "public_slug"},
                    headers=headers,
                ),
            )
            if menu_res.status_code == 200 and menu_res.json():
                items, sold_out = _store_rows_to_menu(menu_res.json())
                if items or sold_out:
                    config.menu_items = items
                    config.sold_out_items = sold_out
            if menus_res.status_code == 200 and menus_res.json():
                slug = (menus_res.json()[0].get("public_slug") or "").strip()
                if slug:
                    config.menu_public_url = f"{PUBLIC_MENU_BASE}/m/{slug}"
        except Exception as menu_exc:  # noqa: BLE001 — store read never breaks a call
            logger.warning("menu store read failed for %s (JSONB fallback): %s",
                           merchant_id, menu_exc)
        # Cache the fully-resolved config (incl. menu-store enrichment) — only
        # real hits are stored, so a just-activated merchant is not pinned to a
        # miss (see _cache_put).
        _cache_put(f"cfg:{merchant_id}", config)
        return config
    except Exception as e:
        logger.error("Failed to load merchant config: %s", e)
        return None


async def get_merchant_by_phone(phone_number: str) -> Optional[str]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return "demo-merchant"

    cached = _cache_get(f"phone:{phone_number}")
    if cached is not None:
        return cached

    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        # params= so E.164 numbers percent-encode: a literal "+" in the query
        # string decodes to a space at the gateway and matches nothing.
        res = await _get_http_client().get(
            f"{SUPABASE_URL}/rest/v1/phone_agent_config",
            params={"phone_number": f"eq.{phone_number}", "select": "merchant_id"},
            headers=headers,
        )
        if res.status_code == 200 and res.json():
            mid = res.json()[0]["merchant_id"]
            _cache_put(f"phone:{phone_number}", mid)
            return mid
    except Exception as e:
        logger.error("Failed to lookup merchant by phone: %s", e)
    return None


def is_open_now(business_hours: dict | None, tz_name: str | None, now: datetime | None = None) -> bool:
    """Is the business open right now, per its configured hours + timezone?

    Returns True (do not gate) unless we can confidently say it's closed:
      - no business_hours configured        → True  (merchant hasn't opted in)
      - no/invalid timezone configured       → True  (can't evaluate safely; the
        old code compared local hours to UTC, which mis-gated — we refuse to
        guess rather than tell an open merchant they're closed)
      - today missing / marked closed        → False
      - current local time outside open–close → False

    ``now`` is injectable for testing (must be tz-aware if provided).
    """
    if not business_hours:
        return True
    if not tz_name:
        return True
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 — unknown tz → don't gate
        return True

    local = now.astimezone(tz) if now else datetime.now(tz)
    day_name = local.strftime("%A").lower()
    hours = business_hours.get(day_name)
    if not hours or hours.get("closed"):
        return False

    open_time = hours.get("open", "00:00")
    close_time = hours.get("close", "23:59")
    current_time = local.strftime("%H:%M")
    return open_time <= current_time <= close_time


def is_within_business_hours(config: MerchantPhoneConfig) -> bool:
    """Back-compat wrapper around is_open_now using the config's tz."""
    return is_open_now(config.business_hours, config.business_timezone or None)


def _demo_config(merchant_id: str) -> MerchantPhoneConfig:
    return MerchantPhoneConfig(
        merchant_id=merchant_id,
        business_name="Tony's Pizza",
        business_type="restaurant",
        phone_number="+15555550100",
        greeting="Thanks for calling Tony's Pizza — this is Meridian's live ordering demo, so nothing gets charged. What can I get started for you?",
        voice="af_bella",
        language="en",
        active=True,
        # Single source of truth for pricing — must mirror the Vapi assistant's
        # spoken menu (assistant 13e00df9) so phoned-in orders price correctly.
        # Pizzas: per-size pricing (12" medium / 16" large) + $2/topping.
        menu_items=[
            {"name": "Cheese Pizza", "sizes": ["medium", "large"], "size_prices": {"medium": 14, "large": 18}, "topping_price": 2.0,
             "modifications": ["pepperoni", "mushroom", "onion", "sausage", "extra cheese", "peppers", "olives"]},
            {"name": "Pepperoni Pizza", "sizes": ["medium", "large"], "size_prices": {"medium": 16, "large": 20}, "topping_price": 2.0,
             "modifications": ["mushroom", "onion", "sausage", "extra cheese", "peppers", "olives"]},
            {"name": "Margherita Pizza", "sizes": ["medium", "large"], "size_prices": {"medium": 16, "large": 20}, "topping_price": 2.0,
             "modifications": ["mushroom", "onion", "sausage", "extra cheese", "peppers", "olives"]},
            {"name": "Meat Lovers Pizza", "sizes": ["medium", "large"], "size_prices": {"medium": 19, "large": 24}, "topping_price": 2.0,
             "modifications": ["mushroom", "onion", "extra cheese", "peppers", "olives"]},
            {"name": "Veggie Pizza", "sizes": ["medium", "large"], "size_prices": {"medium": 17, "large": 22}, "topping_price": 2.0,
             "modifications": ["mushroom", "onion", "extra cheese", "peppers", "olives"]},
            {"name": "Garlic Bread", "price": 6.0},
            {"name": "Caesar Salad", "price": 9.0},
            {"name": "Wings", "price": 12.0, "modifications": ["mild", "medium", "hot", "bbq"]},
            {"name": "Mozzarella Sticks", "price": 8.0},
            {"name": "Coke", "price": 3.0},
            {"name": "Diet Coke", "price": 3.0},
            {"name": "Sprite", "price": 3.0},
            {"name": "Water", "price": 3.0},
        ],
        pos_system="square",
        pos_access_token="",
        pos_location_id="",
        business_hours={},
        after_hours_message="Thank you for calling. We are currently closed.",
        max_concurrent_calls=5,
        order_types=["pickup", "delivery", "dine_in"],
        special_instructions_enabled=True,
        transfer_number="",
        pos_webhook_url="",
        # Public demo line: NEVER text real Stripe payment links — a stranger
        # paying for demo pizza is a refund/dispute, not revenue.
        sms_checkout_enabled=False,
        sms_ordering_enabled=True,
        tax_rate=0.13,
        payment_mode="pay_now",
        # This config is also the fallback for a dialed number with NO merchant
        # row (unknown/ported/mid-provision DID). demo_safe makes that fallback
        # provably harmless: the POS connector + payment path are logs-only, so
        # a real caller reaching it can never trigger a real order or charge —
        # they hear the "nothing gets charged" demo, not a phantom live order.
        demo_safe=True,
        # Demo line leads with the "Vinny" character (premium ElevenLabs voice
        # + NY pizzeria persona) — the flagship sales demo. customGreeting
        # keeps the required "nothing gets charged" disclosure, which a bare
        # persona greeting template would drop.
        personality={
            "character": "vinny",
            "customGreeting": (
                "Ay, Tony's Pizza, this is Vinny! This here's Meridian's live "
                "demo — nothin' gets charged, capisce? Now whaddya havin' "
                "today, my friend?"
            ),
        },
    )
