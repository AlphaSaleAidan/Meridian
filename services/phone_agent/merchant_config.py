"""
Merchant configuration loader.
Pulls merchant settings from Supabase for phone agent behavior.
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger("meridian.phone_agent.config")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")


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
    # PER-RESTAURANT PERSONALIZATION BRIEF ──────────────────────────────
    # Generated on demand via POST /api/phone/build-brief/{merchant_id}.
    # Injected into the system prompt for tone/warmth only — the MENU is
    # still the single source of truth for items and prices.
    # Empty string = no brief = prompt is byte-for-byte unchanged (no regression).
    website_url: str = ""
    restaurant_brief: str = ""
    # RESERVATIONS: hand-off to the restaurant's EXISTING rez system. When
    # enabled and a URL is set, the agent texts callers the booking link
    # (send_reservation_link tool) — Meridian never books tables itself.
    reservations_enabled: bool = False
    reservation_url: str = ""
    reservation_platform: str = ""


def reservations_on(config) -> bool:
    """True when the reservation hand-off tool should be exposed:
    reservations enabled AND a booking URL set. Shared by both agent stacks
    (Pipecat bot.py and the Vapi webhook route)."""
    return bool(getattr(config, "reservations_enabled", False)
                and getattr(config, "reservation_url", ""))


_VALID_PAYMENT_MODES = ("pay_now", "pay_at_pickup", "optional")


def _norm_payment_mode(value: Optional[str]) -> str:
    """Normalize the configured payment_mode; unknown/missing → pay_now (default)."""
    mode = (value or "").strip().lower()
    return mode if mode in _VALID_PAYMENT_MODES else "pay_now"


async def get_merchant_config(merchant_id: str) -> Optional[MerchantPhoneConfig]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("No Supabase configured — using demo config for %s", merchant_id)
        return _demo_config(merchant_id)

    try:
        import httpx

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/phone_agent_config"
                f"?merchant_id=eq.{merchant_id}&select=*",
                headers=headers,
            )
            if res.status_code != 200 or not res.json():
                logger.warning("No phone config for merchant %s", merchant_id)
                return None

            row = res.json()[0]
            return MerchantPhoneConfig(
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
                # Default to pay_now if the column is missing/null (anti-scam default).
                payment_mode=_norm_payment_mode(row.get("payment_mode")),
                business_timezone=(row.get("business_timezone") or "").strip(),
                stripe_account_id=(row.get("stripe_account_id") or "").strip(),
                stripe_charges_enabled=bool(row.get("stripe_charges_enabled")),
                demo_safe=bool(row.get("demo_safe", False)),
                website_url=(row.get("website_url") or "").strip(),
                restaurant_brief=(row.get("restaurant_brief") or "").strip(),
                reservations_enabled=bool(row.get("reservations_enabled", False)),
                reservation_url=(row.get("reservation_url") or "").strip(),
                reservation_platform=(row.get("reservation_platform") or "").strip(),
            )
    except Exception as e:
        logger.error("Failed to load merchant config: %s", e)
        return None


async def get_merchant_by_phone(phone_number: str) -> Optional[str]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return "demo-merchant"

    try:
        import httpx

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/phone_agent_config"
                f"?phone_number=eq.{phone_number}&select=merchant_id",
                headers=headers,
            )
            if res.status_code == 200 and res.json():
                return res.json()[0]["merchant_id"]
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
        greeting="Thanks for calling Tony's Pizza! What can I get started for you?",
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
        sms_checkout_enabled=True,
        sms_ordering_enabled=True,
        tax_rate=0.13,
        payment_mode="pay_now",
    )
