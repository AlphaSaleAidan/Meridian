"""
Webhook Delivery Service — Reliable outbound webhook dispatch.

Features:
  - Exponential backoff with jitter (3 retries)
  - Dead letter queue after max retries
  - HMAC-SHA256 request signatures
  - Delivery attempt tracking
"""
import hashlib
import hmac
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import httpx

logger = logging.getLogger("meridian.webhooks.delivery")


@dataclass
class DeliveryAttempt:
    attempt_number: int
    status_code: Optional[int] = None
    error: Optional[str] = None
    duration_ms: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class WebhookDelivery:
    id: str
    url: str
    event_type: str
    payload: dict
    org_id: str
    status: str = "pending"  # pending, delivered, failed, dead_letter
    attempts: list[DeliveryAttempt] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def sign_payload(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


async def deliver_webhook(
    url: str,
    event_type: str,
    payload: dict,
    org_id: str,
    signing_secret: Optional[str] = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> WebhookDelivery:
    """Deliver a webhook with exponential backoff and HMAC signing."""
    delivery = WebhookDelivery(
        id=str(uuid4()),
        url=url,
        event_type=event_type,
        payload=payload,
        org_id=org_id,
    )

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    body_bytes = body.encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Meridian-Event": event_type,
        "X-Meridian-Delivery": delivery.id,
        "X-Meridian-Timestamp": delivery.created_at,
    }

    if signing_secret:
        signature = sign_payload(body_bytes, signing_secret)
        headers["X-Meridian-Signature"] = f"sha256={signature}"

    async with httpx.AsyncClient() as client:
        for attempt in range(1, max_retries + 1):
            start = time.monotonic()
            try:
                resp = await client.post(
                    url,
                    content=body_bytes,
                    headers=headers,
                    timeout=30.0,
                )
                duration_ms = round((time.monotonic() - start) * 1000, 1)

                delivery.attempts.append(DeliveryAttempt(
                    attempt_number=attempt,
                    status_code=resp.status_code,
                    duration_ms=duration_ms,
                ))

                if resp.status_code in (200, 201, 202, 204):
                    delivery.status = "delivered"
                    logger.info(
                        f"Webhook delivered: {event_type} → {url} "
                        f"(attempt {attempt}, {duration_ms}ms)"
                    )
                    return delivery

                logger.warning(
                    f"Webhook attempt {attempt} failed: {resp.status_code} "
                    f"for {event_type} → {url}"
                )

            except Exception as e:
                duration_ms = round((time.monotonic() - start) * 1000, 1)
                delivery.attempts.append(DeliveryAttempt(
                    attempt_number=attempt,
                    error=str(e),
                    duration_ms=duration_ms,
                ))
                logger.warning(f"Webhook attempt {attempt} error: {e}")

            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                import asyncio
                await asyncio.sleep(delay)

    delivery.status = "dead_letter"
    logger.error(f"Webhook dead-lettered after {max_retries} attempts: {event_type} → {url}")
    return delivery
