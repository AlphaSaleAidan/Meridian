"""
Webhook Registry — Merchant webhook endpoint registration.

Merchants register URLs to receive real-time events:
  - insight.generated
  - alert.fired
  - report.ready
  - anomaly.detected
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

logger = logging.getLogger("meridian.webhooks.registry")

SUPPORTED_EVENTS = [
    "insight.generated",
    "alert.fired",
    "report.ready",
    "anomaly.detected",
    "sync.completed",
]


async def register_webhook(
    db,
    org_id: str,
    url: str,
    events: list[str],
    secret: Optional[str] = None,
) -> dict:
    """Register a webhook endpoint for a merchant."""
    invalid = [e for e in events if e not in SUPPORTED_EVENTS]
    if invalid:
        return {"error": f"Unsupported events: {invalid}", "supported": SUPPORTED_EVENTS}

    webhook_id = str(uuid4())
    record = {
        "id": webhook_id,
        "org_id": org_id,
        "url": url,
        "events": events,
        "secret": secret or "",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.insert("webhook_registrations", record)
    logger.info(f"Webhook registered: {webhook_id} for {org_id} → {url}")

    return {"id": webhook_id, "url": url, "events": events, "status": "active"}


async def list_webhooks(db, org_id: str) -> list[dict]:
    """List all registered webhooks for a merchant."""
    rows = await db.query(
        "webhook_registrations",
        select="id, url, events, active, created_at",
        filters={"org_id": f"eq.{org_id}"},
    )
    return rows


async def delete_webhook(db, org_id: str, webhook_id: str) -> dict:
    """Deactivate a webhook registration."""
    await db.update(
        "webhook_registrations",
        {"active": False},
        filters={"id": f"eq.{webhook_id}", "org_id": f"eq.{org_id}"},
    )
    return {"id": webhook_id, "status": "deleted"}


async def get_webhooks_for_event(db, org_id: str, event_type: str) -> list[dict]:
    """Get all active webhook URLs subscribed to an event type."""
    rows = await db.query(
        "webhook_registrations",
        select="id, url, secret, events",
        filters={"org_id": f"eq.{org_id}", "active": "eq.true"},
    )
    return [r for r in rows if event_type in r.get("events", [])]


async def list_deliveries(db, org_id: str, limit: int = 50) -> list[dict]:
    """List recent webhook delivery attempts."""
    rows = await db.query(
        "webhook_deliveries",
        select="id, event_type, url, status, attempts, created_at",
        filters={"org_id": f"eq.{org_id}"},
        order="created_at.desc",
        limit=limit,
    )
    return rows
