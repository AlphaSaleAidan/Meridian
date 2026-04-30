"""
Customer App Sync — Push processed data to the Meridian customer portal.

After the AI engine generates insights, forecasts, and revenue data in
Supabase, this module pushes the results to the customer-facing Convex app
via its HTTP ingest API.

The customer app (Viktor Space) runs on Convex and exposes these endpoints:
    POST /api/ingest/sync          — Full sync (org + insights + forecasts + revenue)
    POST /api/ingest/organization  — Upsert one org
    POST /api/ingest/insights      — Batch upsert insights
    POST /api/ingest/forecasts     — Batch upsert forecasts
    POST /api/ingest/revenue       — Revenue data points
    GET  /api/ingest/health        — Health check

Configuration via environment variables:
    CUSTOMER_APP_INGEST_URL    — Base URL (default: Convex site URL)
    CUSTOMER_APP_INGEST_SECRET — Bearer token for auth
"""
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("meridian.sync.customer_app")

# ─── Configuration ────────────────────────────────────────

CUSTOMER_APP_INGEST_URL = os.getenv(
    "CUSTOMER_APP_INGEST_URL",
    "https://industrious-rabbit-343.convex.site",
)

CUSTOMER_APP_INGEST_SECRET = os.getenv(
    "CUSTOMER_APP_INGEST_SECRET",
    "meridian-ingest-2026",
)

# Timeout for HTTP calls (seconds)
INGEST_TIMEOUT = 30


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {CUSTOMER_APP_INGEST_SECRET}",
        "Content-Type": "application/json",
    }


# ─── Health Check ─────────────────────────────────────────

async def check_health() -> bool:
    """Check if the customer app ingest API is reachable."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{CUSTOMER_APP_INGEST_URL}/api/ingest/health"
            )
            data = resp.json()
            return data.get("status") == "ok"
    except Exception as e:
        logger.warning(f"Customer app health check failed: {e}")
        return False


# ─── Full Sync ────────────────────────────────────────────

async def sync_to_customer_app(
    org_id: str,
    org_name: str = "Business",
    business_type: str | None = None,
    plan: str = "starter",
    status: str = "active",
    monthly_revenue: int | None = None,
    locations_count: int | None = None,
    products_count: int | None = None,
    transactions_count: int | None = None,
    insights: list[dict] | None = None,
    forecasts: list[dict] | None = None,
    revenue_data: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Push all processed data to the customer app in a single call.

    This should be called at the end of:
      - Full sync pipeline (after AI analysis)
      - Backfill worker (after initial import + AI)
      - Incremental sync worker (if insights are refreshed)

    Returns:
        dict with sync results or error info
    """
    payload: dict[str, Any] = {
        "orgId": org_id,
        "organization": {
            "name": org_name,
            "businessType": business_type,
            "plan": plan,
            "status": status,
        },
    }

    # Add optional org fields
    if monthly_revenue is not None:
        payload["organization"]["monthlyRevenue"] = monthly_revenue
    if locations_count is not None:
        payload["organization"]["locationsCount"] = locations_count
    if products_count is not None:
        payload["organization"]["productsCount"] = products_count
    if transactions_count is not None:
        payload["organization"]["transactionsCount"] = transactions_count

    # Add insights
    if insights:
        payload["insights"] = insights

    # Add forecasts
    if forecasts:
        payload["forecasts"] = forecasts

    # Add revenue data
    if revenue_data:
        payload["dataPoints"] = revenue_data

    logger.info(
        f"Syncing to customer app: org={org_id}, "
        f"insights={len(insights or [])}, "
        f"forecasts={len(forecasts or [])}, "
        f"revenue_points={len(revenue_data or [])}"
    )

    try:
        async with httpx.AsyncClient(timeout=INGEST_TIMEOUT) as client:
            resp = await client.post(
                f"{CUSTOMER_APP_INGEST_URL}/api/ingest/sync",
                json=payload,
                headers=_headers(),
            )

            if resp.status_code == 200:
                result = resp.json()
                logger.info(f"✅ Customer app sync success: {result}")
                return result
            else:
                error_text = resp.text
                logger.error(
                    f"Customer app sync failed: HTTP {resp.status_code} — {error_text}"
                )
                return {"success": False, "error": error_text, "status": resp.status_code}

    except httpx.TimeoutException:
        logger.error(f"Customer app sync timed out after {INGEST_TIMEOUT}s")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        logger.error(f"Customer app sync error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ─── Individual Endpoint Helpers ──────────────────────────

async def sync_insights(org_id: str, insights: list[dict]) -> dict:
    """Push only insights to the customer app."""
    try:
        async with httpx.AsyncClient(timeout=INGEST_TIMEOUT) as client:
            resp = await client.post(
                f"{CUSTOMER_APP_INGEST_URL}/api/ingest/insights",
                json={"orgId": org_id, "insights": insights},
                headers=_headers(),
            )
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to sync insights: {e}")
        return {"success": False, "error": str(e)}


async def sync_forecasts(org_id: str, forecasts: list[dict]) -> dict:
    """Push only forecasts to the customer app."""
    try:
        async with httpx.AsyncClient(timeout=INGEST_TIMEOUT) as client:
            resp = await client.post(
                f"{CUSTOMER_APP_INGEST_URL}/api/ingest/forecasts",
                json={"orgId": org_id, "forecasts": forecasts},
                headers=_headers(),
            )
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to sync forecasts: {e}")
        return {"success": False, "error": str(e)}


async def sync_revenue(org_id: str, data_points: list[dict]) -> dict:
    """Push only revenue data to the customer app."""
    try:
        async with httpx.AsyncClient(timeout=INGEST_TIMEOUT) as client:
            resp = await client.post(
                f"{CUSTOMER_APP_INGEST_URL}/api/ingest/revenue",
                json={"orgId": org_id, "dataPoints": data_points},
                headers=_headers(),
            )
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to sync revenue data: {e}")
        return {"success": False, "error": str(e)}
