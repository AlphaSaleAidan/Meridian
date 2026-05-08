"""
Merchant configuration loader.
Pulls merchant settings from Supabase for phone agent behavior.
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
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


def is_within_business_hours(config: MerchantPhoneConfig) -> bool:
    if not config.business_hours:
        return True

    now = datetime.now(timezone.utc)
    day_name = now.strftime("%A").lower()
    hours = config.business_hours.get(day_name)

    if not hours:
        return False
    if hours.get("closed"):
        return False

    open_time = hours.get("open", "00:00")
    close_time = hours.get("close", "23:59")
    current_time = now.strftime("%H:%M")

    return open_time <= current_time <= close_time


def _demo_config(merchant_id: str) -> MerchantPhoneConfig:
    return MerchantPhoneConfig(
        merchant_id=merchant_id,
        business_name="Demo Restaurant",
        business_type="restaurant",
        phone_number="+15555550100",
        greeting="Thank you for calling Demo Restaurant! How can I help you today?",
        voice="af_bella",
        language="en",
        active=True,
        menu_items=[
            {"name": "Cheeseburger", "price": 12.99, "sizes": ["regular", "double"]},
            {"name": "Chicken Sandwich", "price": 11.49, "sizes": ["regular"]},
            {"name": "French Fries", "price": 4.99, "sizes": ["small", "medium", "large"]},
            {"name": "Coca-Cola", "price": 2.99, "sizes": ["small", "medium", "large"]},
            {"name": "Milkshake", "price": 6.99, "sizes": ["regular"], "modifications": ["chocolate", "vanilla", "strawberry"]},
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
    )
