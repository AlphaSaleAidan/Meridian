"""
Real-Time Anomaly Detection Flow — Webhook-triggered analysis.

Triggered when POS webhooks arrive (new transaction, inventory change).
Runs anomaly-focused agents only — fast path, not full analysis.
"""
import logging

from prefect import flow, task

logger = logging.getLogger("meridian.workflows.realtime")


@task(retries=3, retry_delay_seconds=30, log_prints=True)
async def detect_revenue_anomaly(org_id: str, transaction: dict) -> dict | None:
    """Check if a transaction triggers a revenue anomaly alert."""
    from ..db import init_db, close_db
    from ..ai.engine import AnalysisContext

    db = await init_db()
    if not db:
        return None

    try:
        daily = await db.get_daily_revenue(org_id, days=30)
        ctx = AnalysisContext(
            org_id=org_id,
            daily_revenue=[dict(r) for r in daily],
            transactions=[transaction],
        )
        from ..ai.agents.revenue_trend import RevenueTrendAgent

        agent = RevenueTrendAgent(ctx)
        result = await agent.analyze()

        anomalies = result.get("anomalies", []) if isinstance(result, dict) else []
        if anomalies:
            logger.warning(f"Revenue anomaly detected for {org_id}: {anomalies}")
            return {"org_id": org_id, "type": "revenue_anomaly", "anomalies": anomalies}
        return None
    finally:
        await close_db()


@task(retries=3, retry_delay_seconds=30, log_prints=True)
async def detect_inventory_anomaly(org_id: str, inventory_update: dict) -> dict | None:
    """Check if an inventory change triggers an alert."""
    from ..db import init_db, close_db
    from ..ai.engine import AnalysisContext

    db = await init_db()
    if not db:
        return None

    try:
        inventory = await db.get_inventory_current(org_id)
        ctx = AnalysisContext(
            org_id=org_id,
            inventory=[dict(r) for r in inventory],
        )
        from ..ai.agents.inventory_intel import InventoryIntelAgent

        agent = InventoryIntelAgent(ctx)
        result = await agent.analyze()

        alerts = result.get("alerts", []) if isinstance(result, dict) else []
        if alerts:
            logger.warning(f"Inventory anomaly detected for {org_id}: {alerts}")
            return {"org_id": org_id, "type": "inventory_anomaly", "alerts": alerts}
        return None
    finally:
        await close_db()


@task(retries=2, retry_delay_seconds=10, log_prints=True)
async def persist_anomaly_alert(org_id: str, anomaly: dict):
    """Save anomaly alert to DB, trigger notification, and email the owner."""
    from ..db import init_db, close_db

    db = await init_db()
    if not db:
        return

    try:
        anomaly_type = anomaly.get("type", "unknown")
        severity = "high"
        title = f"Anomaly detected: {anomaly_type}"

        await db.insert("notifications", {
            "org_id": org_id,
            "type": anomaly_type,
            "severity": severity,
            "title": title,
            "payload": anomaly,
            "read": False,
        })
        logger.info(f"Anomaly alert persisted for {org_id}")

        orgs = await db.select("organizations", filters={"id": f"eq.{org_id}"}, limit=1)
        if orgs:
            org = orgs[0]
            email = org.get("email") or org.get("contact_email")
            if email:
                from ..email.send import send_anomaly_alert
                details = anomaly.get("anomalies") or anomaly.get("alerts") or []
                detail_text = "; ".join(str(d) for d in details[:3]) if details else str(anomaly)
                await send_anomaly_alert(
                    to=email,
                    business_name=org.get("name", "Your Business"),
                    alert_title=title,
                    alert_detail=detail_text,
                    severity=severity,
                    org_id=org_id,
                )
    finally:
        await close_db()


@flow(
    name="realtime-anomaly-detection",
    description="Webhook-triggered anomaly detection on new POS events",
    timeout_seconds=120,
)
async def realtime_anomaly(
    org_id: str,
    event_type: str,
    payload: dict,
):
    """
    Real-time anomaly detection triggered by POS webhooks.

    Runs only anomaly-focused agents for fast response.
    """
    logger.info(f"Anomaly check for {org_id}: event={event_type}")

    anomaly = None

    if event_type in ("payment.created", "order.created", "order.updated"):
        anomaly = await detect_revenue_anomaly(org_id, payload)
    elif event_type in ("inventory.count.updated",):
        anomaly = await detect_inventory_anomaly(org_id, payload)
    else:
        logger.debug(f"No anomaly handler for event type: {event_type}")
        return {"status": "skipped", "reason": f"unhandled_event: {event_type}"}

    if anomaly:
        await persist_anomaly_alert(org_id, anomaly)
        return {"status": "alert_fired", "anomaly": anomaly}

    return {"status": "clean", "event_type": event_type}
