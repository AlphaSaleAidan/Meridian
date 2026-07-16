"""
Order Dispatcher — Routes phone agent orders to the correct POS system.

The phone agent (Twilio voice) collects order details and calls this
dispatcher. For systems with order APIs (Tier 1-2), we push directly.
For CSV-only systems, we fall back to SMS/email notification to the
merchant with order details formatted for manual entry.

Fallback chain: API → SMS → Email → Queue for manual processing.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from .base import OrderResult, POSConnectionConfig
from .registry import get_connector_config, SYSTEM_CONFIGS
from .rest_connector import GenericRESTConnector

logger = logging.getLogger("meridian.pos.order_dispatcher")


async def create_pos_order(
    system_key: str,
    order_data: dict,
    config: POSConnectionConfig | None = None,
) -> OrderResult:
    api_config = get_connector_config(system_key)
    if not api_config:
        return OrderResult(
            success=False,
            pos_system=system_key,
            fallback_used=True,
            fallback_reason=f"Unknown POS system: {system_key}",
        )

    if api_config.get("auth_type") == "csv_only" or not api_config.get("supports_orders"):
        return await _fallback_order(system_key, order_data, api_config)

    if config is None:
        return OrderResult(
            success=False,
            pos_system=system_key,
            fallback_used=True,
            fallback_reason="No connection config provided — cannot authenticate to POS",
        )

    try:
        connector = GenericRESTConnector(config, api_config)
        result = await connector.create_order(order_data)

        if not result.success:
            logger.warning(f"[{system_key}] API order failed, trying fallback: {result.fallback_reason}")
            return await _fallback_order(
                system_key, order_data, api_config,
                api_result={"attempted": True, "sent": False,
                            "error": result.fallback_reason or "api_error"},
            )

        # Record what actually delivered the order so callers/support can see it
        # (channel ledger, mirrors the phone-agent fan-out columns).
        result.raw_response.setdefault(
            "channel_results", {"api": {"attempted": True, "sent": True}}
        )
        return result

    except Exception as e:
        logger.error(f"[{system_key}] Order dispatch error: {e}")
        return await _fallback_order(
            system_key, order_data, api_config,
            api_result={"attempted": True, "sent": False, "error": str(e)},
        )


async def _fallback_order(
    system_key: str,
    order_data: dict,
    api_config: dict,
    api_result: dict | None = None,
) -> OrderResult:
    order_id = _generate_fallback_order_id(system_key, order_data)

    merchant_phone = order_data.get("merchant_phone")
    merchant_email = order_data.get("merchant_email")
    merchant_name = order_data.get("merchant_name", system_key)

    message = _format_order_message(order_data, merchant_name)

    # Channel ledger: record every attempt (and every skip + why), not just the
    # first success — support must be able to see exactly what fired and failed.
    channel_results: dict = {
        "api": api_result or {"attempted": False, "reason": "no direct API"},
    }

    sent_via = None

    if merchant_phone:
        sent = await _send_sms(merchant_phone, message)
        channel_results["sms"] = {"attempted": True, "sent": sent}
        if sent:
            sent_via = "sms"
    else:
        channel_results["sms"] = {"attempted": False, "reason": "no merchant phone on file"}

    if not sent_via:
        if merchant_email:
            sent = await _send_email(merchant_email, "New Phone Order", message)
            channel_results["email"] = {"attempted": True, "sent": sent}
            if sent:
                sent_via = "email"
        else:
            channel_results["email"] = {"attempted": False, "reason": "no merchant email on file"}
    else:
        channel_results["email"] = {"attempted": False, "reason": "sms already delivered"}

    if not sent_via:
        # Nothing actually delivered the order (no API, no merchant SMS/email).
        # "queued" was a log line with no real queue — report FAILURE so callers
        # don't confirm an order that vanished. SMS/email paths still succeed.
        logger.error(f"[{system_key}] Order {order_id} NOT delivered (no API, no SMS/email) — failing")
        return OrderResult(
            success=False,
            order_id=order_id,
            pos_system=system_key,
            fallback_used=True,
            fallback_reason="Undelivered: no POS API and no merchant phone/email on file",
            raw_response={"delivery_method": "none", "message": message,
                          "channel_results": channel_results},
        )

    return OrderResult(
        success=True,
        order_id=order_id,
        pos_system=system_key,
        fallback_used=True,
        fallback_reason=f"Sent via {sent_via} (no direct API)",
        raw_response={"delivery_method": sent_via, "message": message,
                      "channel_results": channel_results},
    )


def _generate_fallback_order_id(system_key: str, order_data: dict) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    items_str = str(order_data.get("items", []))
    hash_input = f"{system_key}:{ts}:{items_str}"
    short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
    return f"MRD-{ts[-6:]}-{short_hash.upper()}"


def _format_order_message(order_data: dict, merchant_name: str) -> str:
    lines = [
        f"📱 NEW PHONE ORDER — {merchant_name}",
        f"Customer: {order_data.get('customer_name', 'Walk-in')}",
        f"Type: {order_data.get('order_type', 'pickup').upper()}",
        "",
        "Items:",
    ]

    for item in order_data.get("items", []):
        qty = item.get("quantity", 1)
        name = item.get("name", "Unknown item")
        special = item.get("special_instructions", "")
        line = f"  • {qty}x {name}"
        if special:
            line += f" [{special}]"
        lines.append(line)

    if order_data.get("special_instructions"):
        lines.append("")
        lines.append(f"Notes: {order_data['special_instructions']}")

    if order_data.get("pickup_time"):
        lines.append(f"Pickup: {order_data['pickup_time']}")

    lines.append("")
    lines.append("— Meridian AI Phone Agent")

    return "\n".join(lines)


async def _send_sms(phone: str, message: str) -> bool:
    try:
        from ..twilio_client import send_sms
        await send_sms(phone, message)
        return True
    except ImportError:
        logger.debug("Twilio client not available for SMS fallback")
        return False
    except Exception as e:
        logger.warning(f"SMS send failed: {e}")
        return False


async def _send_email(email: str, subject: str, body: str) -> bool:
    try:
        from ..email_client import send_email
        await send_email(to=email, subject=subject, body=body)
        return True
    except ImportError:
        logger.debug("Email client not available for fallback")
        return False
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        return False


def get_order_routing_info(system_key: str) -> dict[str, Any]:
    api_config = get_connector_config(system_key)
    if not api_config:
        return {"system_key": system_key, "route": "unknown", "supports_api_orders": False}

    supports_api = (
        api_config.get("auth_type") != "csv_only"
        and api_config.get("supports_orders", False)
    )

    return {
        "system_key": system_key,
        "route": "api" if supports_api else "fallback",
        "supports_api_orders": supports_api,
        "fallback_methods": ["sms", "email", "queue"] if not supports_api else [],
        "category": api_config.get("category", "restaurant"),
    }


def get_all_order_capable_systems() -> list[dict[str, Any]]:
    results = []
    for key, cfg in SYSTEM_CONFIGS.items():
        if cfg.get("supports_orders"):
            results.append({
                "system_key": key,
                "route": "api",
                "category": cfg.get("category", "restaurant"),
            })
    return results
