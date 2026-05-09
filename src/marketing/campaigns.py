"""
Marketing Campaign Triggers — Agent-driven automation.

Maps AI agent outputs to marketing actions:
  - At-risk customer → win-back campaign
  - Promo lift detected → performance report
  - Churn predicted → retention sequence
  - Revenue anomaly → alert notification

Dispatches via webhook to Mautic/Dittofeed/Mailchimp.
"""
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

from .templates import render_template

logger = logging.getLogger("meridian.marketing")

WEBHOOK_URL = os.environ.get("MARKETING_WEBHOOK_URL", "")
WEBHOOK_SECRET = os.environ.get("MARKETING_WEBHOOK_SECRET", "")


@dataclass
class CampaignTrigger:
    campaign_type: str
    org_id: str
    customer_ids: list[str]
    context: dict[str, Any]
    template: str


def evaluate_triggers(org_id: str, agent_outputs: dict[str, Any]) -> list[CampaignTrigger]:
    """Evaluate agent outputs and return campaign triggers."""
    triggers: list[CampaignTrigger] = []

    ltv_output = agent_outputs.get("customer_ltv", {})
    if isinstance(ltv_output, dict) and ltv_output.get("status") == "complete":
        at_risk = ltv_output.get("at_risk_customers", [])
        if at_risk:
            triggers.append(CampaignTrigger(
                campaign_type="win_back",
                org_id=org_id,
                customer_ids=[c["id"] for c in at_risk[:20]],
                context={
                    "total_at_risk": len(at_risk),
                    "avg_ltv_cents": ltv_output.get("avg_ltv_cents", 0),
                },
                template="win_back",
            ))

    promo_output = agent_outputs.get("promo_roi", {})
    if isinstance(promo_output, dict) and promo_output.get("status") == "complete":
        top_promos = promo_output.get("top_performing", [])
        if top_promos:
            triggers.append(CampaignTrigger(
                campaign_type="promo_report",
                org_id=org_id,
                customer_ids=[],
                context={
                    "promos": top_promos[:5],
                    "total_lift_cents": sum(p.get("lift_cents", 0) for p in top_promos),
                },
                template="promo_performance",
            ))

    churn_output = agent_outputs.get("churn_warning", {})
    if not isinstance(churn_output, dict):
        churn_output = {}
    churning = churn_output.get("high_risk_customers", [])
    if churning:
        triggers.append(CampaignTrigger(
            campaign_type="retention",
            org_id=org_id,
            customer_ids=[c["id"] for c in churning[:15]],
            context={
                "total_churning": len(churning),
                "avg_days_since_visit": churn_output.get("avg_days_since_visit", 0),
            },
            template="retention_sequence",
        ))

    return triggers


async def dispatch_campaign(trigger: CampaignTrigger) -> dict[str, Any]:
    """Send campaign trigger to external marketing platform via webhook."""
    if not WEBHOOK_URL:
        logger.warning("MARKETING_WEBHOOK_URL not set — campaign not dispatched")
        return {"status": "skipped", "reason": "no_webhook_url"}

    html_body = render_template(trigger.template, trigger.context)

    payload = {
        "campaign_type": trigger.campaign_type,
        "org_id": trigger.org_id,
        "customer_ids": trigger.customer_ids,
        "context": trigger.context,
        "html_body": html_body,
    }

    headers = {"Content-Type": "application/json"}
    if WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = WEBHOOK_SECRET

    async with httpx.AsyncClient() as client:
        resp = await client.post(WEBHOOK_URL, json=payload, headers=headers, timeout=30)

    if resp.status_code in (200, 201, 202):
        logger.info(f"Campaign dispatched: {trigger.campaign_type} for {trigger.org_id}")
        return {"status": "dispatched", "campaign_type": trigger.campaign_type}

    logger.error(f"Campaign dispatch failed: {resp.status_code} {resp.text}")
    return {"status": "failed", "code": resp.status_code}


async def process_agent_outputs(org_id: str, agent_outputs: dict[str, Any]) -> list[dict]:
    """Evaluate all triggers and dispatch matching campaigns."""
    triggers = evaluate_triggers(org_id, agent_outputs)
    results = []
    for trigger in triggers:
        result = await dispatch_campaign(trigger)
        results.append(result)
    return results
