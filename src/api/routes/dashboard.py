"""
Dashboard API Routes — Powers the Meridian frontend.

All endpoints require org_id (from auth context in production).
For now, accepts org_id as a query parameter.

Routes:
  GET /api/dashboard/overview       → Key metrics + Money Left score
  GET /api/dashboard/revenue        → Daily/weekly revenue data
  GET /api/dashboard/revenue/hourly → Hourly breakdown (heat map)
  GET /api/dashboard/products       → Product performance
  GET /api/dashboard/insights       → Active AI insights
  GET /api/dashboard/forecasts      → Revenue forecasts
  GET /api/dashboard/notifications  → User notifications
  GET /api/dashboard/connection     → POS connection status
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Depends

logger = logging.getLogger("meridian.api.dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _get_db():
    """
    Dependency: returns the global SupabaseREST instance.
    Injected at app startup via `router.dependencies`.
    """
    from ...db import _db_instance
    if _db_instance is None:
        raise HTTPException(503, "Database not initialized")
    return _db_instance


# ─── Overview ─────────────────────────────────────────────

@router.get("/overview")
async def get_overview(
    org_id: str = Query(..., description="Organization ID"),
    db=Depends(_get_db),
):
    """
    Main dashboard overview:
    - Total revenue (30d)
    - Transaction count (30d)
    - Average ticket size
    - Money Left on Table score (latest)
    - Revenue change vs prior period
    - Connection status
    """
    # Fetch data in parallel-ish (sequential for now, can asyncio.gather later)
    daily = await db.get_daily_revenue(org_id, days=60)
    money_left = await db.select(
        "money_left_scores",
        filters={"org_id": f"eq.{org_id}"},
        order="scored_at.desc",
        limit=1,
    )
    connection = await db.get_pos_connection(org_id)

    # Split into current 30d and prior 30d
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=30)).isoformat()

    current = [r for r in daily if r.get("day_bucket", "") >= cutoff]
    prior = [r for r in daily if r.get("day_bucket", "") < cutoff]

    current_revenue = sum(r.get("total_revenue_cents", 0) or 0 for r in current)
    prior_revenue = sum(r.get("total_revenue_cents", 0) or 0 for r in prior)
    current_txns = sum(r.get("transaction_count", 0) or 0 for r in current)
    avg_ticket = current_revenue // current_txns if current_txns else 0

    change_pct = 0
    if prior_revenue > 0:
        change_pct = round((current_revenue - prior_revenue) / prior_revenue * 100, 1)

    return {
        "revenue_cents_30d": current_revenue,
        "revenue_change_pct": change_pct,
        "transaction_count_30d": current_txns,
        "avg_ticket_cents": avg_ticket,
        "money_left_score": money_left[0] if money_left else None,
        "connection": {
            "status": connection.get("status", "disconnected") if connection else "disconnected",
            "provider": connection.get("provider", None) if connection else None,
            "last_sync_at": connection.get("last_sync_at", None) if connection else None,
        },
        "days_with_data": len(current),
    }


# ─── Revenue ──────────────────────────────────────────────

@router.get("/revenue")
async def get_revenue(
    org_id: str = Query(..., description="Organization ID"),
    days: int = Query(30, ge=7, le=365),
    db=Depends(_get_db),
):
    """Daily revenue data for charts."""
    daily = await db.get_daily_revenue(org_id, days=days)
    weekly = await db.select(
        "weekly_revenue",
        filters={
            "org_id": f"eq.{org_id}",
            "week_bucket": f"gte.{(datetime.now(timezone.utc) - timedelta(days=days)).isoformat()}",
        },
        order="week_bucket.asc",
    )

    return {
        "daily": [
            {
                "date": r.get("day_bucket"),
                "revenue_cents": r.get("total_revenue_cents", 0),
                "transactions": r.get("transaction_count", 0),
                "avg_ticket_cents": r.get("avg_ticket_cents", 0),
                "refund_cents": r.get("refund_total_cents", 0),
                "tax_cents": r.get("total_tax_cents", 0),
                "tip_cents": r.get("total_tip_cents", 0),
                "discount_cents": r.get("total_discount_cents", 0),
                "customers": r.get("unique_customers", 0),
            }
            for r in daily
        ],
        "weekly": [
            {
                "week": r.get("week_bucket"),
                "revenue_cents": r.get("total_revenue_cents", 0),
                "transactions": r.get("transaction_count", 0),
                "avg_ticket_cents": r.get("avg_ticket_cents", 0),
            }
            for r in weekly
        ],
    }


@router.get("/revenue/hourly")
async def get_hourly_revenue(
    org_id: str = Query(..., description="Organization ID"),
    days: int = Query(30, ge=7, le=90),
    db=Depends(_get_db),
):
    """Hourly revenue breakdown for heat map / peak hours."""
    hourly = await db.get_hourly_revenue(org_id, days=days)

    return {
        "hourly": [
            {
                "hour": r.get("hour_bucket"),
                "revenue_cents": r.get("total_revenue_cents", 0),
                "sales": r.get("sale_count", 0),
                "refunds": r.get("refund_count", 0),
                "avg_ticket_cents": r.get("avg_ticket_cents", 0),
                "customers": r.get("unique_customers", 0),
                "cash_count": r.get("cash_count", 0),
                "credit_count": r.get("credit_count", 0),
            }
            for r in hourly
        ],
    }


# ─── Products ─────────────────────────────────────────────

@router.get("/products")
async def get_products(
    org_id: str = Query(..., description="Organization ID"),
    days: int = Query(30, ge=7, le=365),
    db=Depends(_get_db),
):
    """Product performance data."""
    products = await db.get_products(org_id)
    performance = await db.get_product_performance(org_id, days=days)

    # Aggregate performance by product
    product_map = {p["id"]: p for p in products}
    perf_by_product: dict[str, dict] = {}

    for row in performance:
        pid = row.get("product_id")
        if pid not in perf_by_product:
            perf_by_product[pid] = {
                "product_id": pid,
                "total_revenue_cents": 0,
                "total_quantity": 0,
                "times_sold": 0,
                "daily": [],
            }
        agg = perf_by_product[pid]
        agg["total_revenue_cents"] += row.get("total_revenue_cents", 0) or 0
        agg["total_quantity"] += row.get("total_quantity", 0) or 0
        agg["times_sold"] += row.get("times_sold", 0) or 0
        agg["daily"].append({
            "date": row.get("day_bucket"),
            "revenue_cents": row.get("total_revenue_cents", 0),
            "quantity": row.get("total_quantity", 0),
        })

    # Merge product info
    result = []
    for pid, perf in perf_by_product.items():
        product = product_map.get(pid, {})
        result.append({
            **perf,
            "name": product.get("name", "Unknown"),
            "sku": product.get("sku"),
            "category_id": product.get("category_id"),
            "price_cents": product.get("price_cents"),
        })

    # Sort by revenue descending
    result.sort(key=lambda x: x["total_revenue_cents"], reverse=True)

    return {
        "products": result,
        "total_products": len(products),
        "period_days": days,
    }


# ─── Insights ─────────────────────────────────────────────

@router.get("/insights")
async def get_insights(
    org_id: str = Query(..., description="Organization ID"),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by action_status"),
    db=Depends(_get_db),
):
    """Active AI-generated insights."""
    filters = {
        "org_id": f"eq.{org_id}",
        "is_active": "eq.true",
    }
    if status:
        filters["action_status"] = f"eq.{status}"

    insights = await db.select(
        "insights",
        filters=filters,
        order="created_at.desc",
        limit=limit,
    )

    return {
        "insights": [
            {
                "id": r.get("id"),
                "type": r.get("type"),
                "title": r.get("title"),
                "summary": r.get("summary"),
                "details": r.get("details", {}),
                "impact_cents": r.get("estimated_monthly_impact_cents"),
                "confidence": r.get("confidence_score"),
                "action_status": r.get("action_status"),
                "valid_until": r.get("valid_until"),
                "created_at": r.get("created_at"),
            }
            for r in insights
        ],
        "total": len(insights),
    }


@router.patch("/insights/{insight_id}/action")
async def update_insight_action(
    insight_id: str,
    action_status: str = Query(..., description="New status: viewed, accepted, dismissed, completed"),
    org_id: str = Query(..., description="Organization ID"),
    db=Depends(_get_db),
):
    """Update an insight's action status."""
    valid_statuses = {"viewed", "accepted", "dismissed", "completed"}
    if action_status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")

    data = {
        "action_status": action_status,
        "actioned_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await db.update(
        "insights",
        data,
        filters={"id": f"eq.{insight_id}", "org_id": f"eq.{org_id}"},
    )

    return {"updated": len(result) > 0, "insight_id": insight_id, "action_status": action_status}


# ─── Forecasts ────────────────────────────────────────────

@router.get("/forecasts")
async def get_forecasts(
    org_id: str = Query(..., description="Organization ID"),
    forecast_type: Optional[str] = Query(None, description="daily_revenue, weekly_revenue, product_demand"),
    db=Depends(_get_db),
):
    """Revenue forecasts."""
    filters = {
        "org_id": f"eq.{org_id}",
        "period_start": f"gte.{datetime.now(timezone.utc).date().isoformat()}",
    }
    if forecast_type:
        filters["forecast_type"] = f"eq.{forecast_type}"

    forecasts = await db.select(
        "forecasts",
        filters=filters,
        order="period_start.asc",
        limit=90,
    )

    return {
        "forecasts": [
            {
                "id": r.get("id"),
                "type": r.get("forecast_type"),
                "period_start": r.get("period_start"),
                "period_end": r.get("period_end"),
                "predicted_cents": r.get("predicted_value_cents"),
                "lower_bound_cents": r.get("lower_bound_cents"),
                "upper_bound_cents": r.get("upper_bound_cents"),
                "confidence": r.get("confidence_score"),
            }
            for r in forecasts
        ],
        "total": len(forecasts),
    }


# ─── Notifications ────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(
    org_id: str = Query(..., description="Organization ID"),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db=Depends(_get_db),
):
    """User notifications (in-app)."""
    filters: dict = {
        "org_id": f"eq.{org_id}",
    }
    if unread_only:
        filters["acknowledged_at"] = "is.null"

    notifications = await db.select(
        "notifications",
        filters=filters,
        order="created_at.desc",
        limit=limit,
    )

    return {
        "notifications": [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "body": r.get("body"),
                "priority": r.get("priority"),
                "source_type": r.get("source_type"),
                "status": r.get("status"),
                "created_at": r.get("created_at"),
                "acknowledged_at": r.get("acknowledged_at"),
            }
            for r in notifications
        ],
        "total": len(notifications),
    }


# ─── Connection Status ───────────────────────────────────

@router.get("/connection")
async def get_connection(
    org_id: str = Query(..., description="Organization ID"),
    db=Depends(_get_db),
):
    """POS connection status and sync info."""
    connections = await db.select(
        "pos_connections",
        filters={"org_id": f"eq.{org_id}"},
        order="created_at.desc",
    )

    return {
        "connections": [
            {
                "id": r.get("id"),
                "provider": r.get("provider"),
                "status": r.get("status"),
                "merchant_id": r.get("merchant_id"),
                "location_ids": r.get("location_ids"),
                "last_sync_at": r.get("last_sync_at"),
                "sync_cursor": r.get("sync_cursor"),
                "historical_import_complete": r.get("historical_import_complete"),
                "last_error": r.get("last_error"),
                "created_at": r.get("created_at"),
            }
            for r in connections
        ],
    }


# ─── Weekly Report ────────────────────────────────────────

@router.get("/weekly-report")
async def get_weekly_report(
    org_id: str = Query(..., description="Organization ID"),
    db=Depends(_get_db),
):
    """Latest weekly report."""
    reports = await db.select(
        "weekly_reports",
        filters={"org_id": f"eq.{org_id}"},
        order="week_end.desc",
        limit=1,
    )

    if not reports:
        return {"report": None}

    r = reports[0]
    return {
        "report": {
            "id": r.get("id"),
            "week_start": r.get("week_start"),
            "week_end": r.get("week_end"),
            "data": r.get("report_data", {}),
            "created_at": r.get("created_at"),
        },
    }
