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
  GET  /api/dashboard/notifications            → User notifications
  POST /api/dashboard/notifications/acknowledge     → Mark one notification read
  POST /api/dashboard/notifications/acknowledge-all → Mark all notifications read
  GET  /api/dashboard/connection                    → POS connection status
"""
import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel

from ..auth import require_admin, require_org_access
from ...db.cache import dashboard_cache, TTL_FAST, TTL_SLOW
from ...db.supabase_rest import SupabaseRESTError

logger = logging.getLogger("meridian.api.dashboard")

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_org_access)],
)

_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
def _validate_org_id(org_id: str = Query(..., description="Organization ID")) -> str:
    if not _UUID_RE.match(org_id) and not org_id.startswith('biz_'):
        raise HTTPException(422, "org_id must be a valid UUID or business ID")
    return org_id


OrgId = Annotated[str, Depends(_validate_org_id)]


def _get_db():
    from ...db import _db_instance
    if _db_instance is None:
        raise HTTPException(503, "Database not initialized")
    return _db_instance


# ─── Overview ─────────────────────────────────────────────

@router.get("/overview")
async def get_overview(
    org_id: OrgId = None,
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
    cache_key = dashboard_cache.make_key("overview", org_id)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    # Pull ~13 months so we can report all-time figures alongside the trailing
    # 30d. A freshly-connected merchant whose backfilled history is all older
    # than 30 days would otherwise see a $0 hero ("connected but nothing shows")
    # even though the data is present — surface the history instead.
    daily, money_left, connection = await asyncio.gather(
        db.get_daily_revenue(org_id, days=400),
        db.select(
            "money_left_scores",
            filters={"org_id": f"eq.{org_id}"},
            order="scored_at.desc",
            limit=1,
        ),
        db.get_pos_connection(org_id),
    )

    # Split into current 30d and prior 30d
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=30)).isoformat()

    current = [r for r in daily if r.get("day_bucket", "") >= cutoff]
    prior_window = (now - timedelta(days=60)).isoformat()
    prior = [r for r in daily if prior_window <= r.get("day_bucket", "") < cutoff]

    current_revenue = sum(r.get("total_revenue_cents", 0) or 0 for r in current)
    prior_revenue = sum(r.get("total_revenue_cents", 0) or 0 for r in prior)
    current_txns = sum(r.get("transaction_count", 0) or 0 for r in current)
    avg_ticket = current_revenue // current_txns if current_txns else 0

    change_pct = 0
    if prior_revenue > 0:
        change_pct = round((current_revenue - prior_revenue) / prior_revenue * 100, 1)

    # All-time (within the ~13mo pull) so history is always visible.
    days_with_data = [r for r in daily if (r.get("total_revenue_cents") or r.get("transaction_count"))]
    lifetime_revenue = sum(r.get("total_revenue_cents", 0) or 0 for r in daily)
    lifetime_txns = sum(r.get("transaction_count", 0) or 0 for r in daily)
    buckets = sorted(r.get("day_bucket", "") for r in days_with_data if r.get("day_bucket"))

    result = {
        "revenue_cents_30d": current_revenue,
        "revenue_change_pct": change_pct,
        "transaction_count_30d": current_txns,
        "avg_ticket_cents": avg_ticket,
        # All-time fields — the frontend falls back to these when the 30d window
        # is empty so backfilled history is still shown.
        "lifetime_revenue_cents": lifetime_revenue,
        "lifetime_transaction_count": lifetime_txns,
        "lifetime_avg_ticket_cents": (lifetime_revenue // lifetime_txns) if lifetime_txns else 0,
        "first_activity_at": buckets[0] if buckets else None,
        "last_activity_at": buckets[-1] if buckets else None,
        "money_left_score": money_left[0] if money_left else None,
        "connection": {
            "status": connection.get("status", "disconnected") if connection else "disconnected",
            "provider": connection.get("provider", None) if connection else None,
            "last_sync_at": connection.get("last_sync_at", None) if connection else None,
        },
        "days_with_data": len(current),
        "lifetime_days_with_data": len(days_with_data),
    }
    dashboard_cache.set(cache_key, result, TTL_FAST)
    return result


# ─── Revenue ──────────────────────────────────────────────

@router.get("/revenue")
async def get_revenue(
    org_id: OrgId,
    days: int = Query(30, ge=7, le=365),
    db=Depends(_get_db),
):
    """Daily revenue data for charts."""
    cache_key = dashboard_cache.make_key("revenue", org_id, days=days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    daily, weekly = await asyncio.gather(
        db.get_daily_revenue(org_id, days=days),
        db.select(
            "weekly_revenue",
            filters={
                "org_id": f"eq.{org_id}",
                "week_bucket": f"gte.{(datetime.now(timezone.utc) - timedelta(days=days)).isoformat()}",
            },
            order="week_bucket.asc",
        ),
    )

    result = {
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
    dashboard_cache.set(cache_key, result, TTL_FAST)
    return result


@router.get("/revenue/annual")
async def get_annual_revenue(
    org_id: OrgId,
    db=Depends(_get_db),
):
    """Historical revenue by calendar year + a monthly series, so merchants can
    see prior-year revenue. Backed by the ~18 months the initial backfill pulls."""
    cache_key = dashboard_cache.make_key("annual", org_id)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    # ~25 months so the current and previous full year both have coverage.
    daily = await db.get_daily_revenue(org_id, days=760)

    by_year: dict[str, dict] = {}
    by_month: dict[str, dict] = {}
    for r in daily:
        bucket = r.get("day_bucket") or ""
        if len(bucket) < 7:
            continue
        year, month = bucket[:4], bucket[:7]
        rev = r.get("total_revenue_cents", 0) or 0
        txns = r.get("transaction_count", 0) or 0
        for key, agg in ((year, by_year), (month, by_month)):
            slot = agg.setdefault(key, {"revenue_cents": 0, "transaction_count": 0})
            slot["revenue_cents"] += rev
            slot["transaction_count"] += txns

    years = [
        {
            "year": int(y),
            "revenue_cents": v["revenue_cents"],
            "transaction_count": v["transaction_count"],
            "avg_ticket_cents": (v["revenue_cents"] // v["transaction_count"]) if v["transaction_count"] else 0,
        }
        for y, v in sorted(by_year.items())
    ]
    monthly = [
        {"month": m, "revenue_cents": v["revenue_cents"], "transaction_count": v["transaction_count"]}
        for m, v in sorted(by_month.items())
    ]

    current_year = years[-1] if years else None
    prior_year = years[-2] if len(years) >= 2 else None
    yoy_pct = None
    if current_year and prior_year and prior_year["revenue_cents"] > 0:
        yoy_pct = round(
            (current_year["revenue_cents"] - prior_year["revenue_cents"]) / prior_year["revenue_cents"] * 100, 1
        )

    result = {
        "years": years,
        "monthly": monthly,
        "current_year": current_year,
        "prior_year": prior_year,
        "yoy_pct": yoy_pct,
    }
    dashboard_cache.set(cache_key, result, TTL_SLOW)
    return result


@router.get("/revenue/hourly")
async def get_hourly_revenue(
    org_id: OrgId,
    days: int = Query(30, ge=7, le=90),
    db=Depends(_get_db),
):
    """Hourly revenue breakdown for heat map / peak hours."""
    cache_key = dashboard_cache.make_key("hourly", org_id, days=days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    hourly = await db.get_hourly_revenue(org_id, days=days)

    result = {
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
    dashboard_cache.set(cache_key, result, TTL_FAST)
    return result


# ─── Products ─────────────────────────────────────────────

@router.get("/products")
async def get_products(
    org_id: OrgId,
    days: int = Query(30, ge=7, le=365),
    db=Depends(_get_db),
):
    """Product performance data."""
    cache_key = dashboard_cache.make_key("products", org_id, days=days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    products, performance = await asyncio.gather(
        db.get_products(org_id),
        db.get_product_performance(org_id, days=days),
    )

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

    # List the FULL catalog — every active product appears, even with no sales
    # in the window. Otherwise a freshly-connected merchant whose only data is
    # older than `days` sees an empty product list while total_products > 0
    # (the "connected but nothing shows" symptom). cost_cents is included so the
    # UI can show true margin where a cost exists (and "needs cost" where null).
    def _row(perf: dict, product: dict) -> dict:
        return {
            **perf,
            "name": product.get("name", "Unknown"),
            "sku": product.get("sku"),
            "category_id": product.get("category_id"),
            "price_cents": product.get("price_cents"),
            "cost_cents": product.get("cost_cents"),
        }

    result = []
    seen_pids = set()
    for product in products:
        pid = product["id"]
        seen_pids.add(pid)
        perf = perf_by_product.get(pid) or {
            "product_id": pid,
            "total_revenue_cents": 0,
            "total_quantity": 0,
            "times_sold": 0,
            "daily": [],
        }
        result.append(_row(perf, product))

    # Keep performance for products no longer in the active catalog
    # (deleted/inactive) so historical sales aren't silently dropped.
    for pid, perf in perf_by_product.items():
        if pid in seen_pids:
            continue
        result.append(_row(perf, product_map.get(pid, {})))

    # Sort by revenue descending, then name so the catalog has a stable order
    result.sort(key=lambda x: (-(x["total_revenue_cents"] or 0), x["name"] or ""))

    response = {
        "products": result,
        "total_products": len(products),
        "period_days": days,
    }
    dashboard_cache.set(cache_key, response, TTL_FAST)
    return response


class ProductCostUpdate(BaseModel):
    cost_cents: int | None = None
    price_cents: int | None = None


@router.patch("/products/{product_id}")
async def update_product_cost(
    product_id: str,
    body: ProductCostUpdate,
    org_id: OrgId = None,
    db=Depends(_get_db),
):
    """Set a product's unit cost (and optionally price) — powers inline cost
    entry on the Products page so margins can compute. Cost-of-goods isn't in
    the POS feed, so the merchant supplies it here once."""
    rows = await db.select(
        "products",
        filters={"id": f"eq.{product_id}", "org_id": f"eq.{org_id}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "Product not found")

    fields: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.cost_cents is not None:
        if body.cost_cents < 0:
            raise HTTPException(422, "cost_cents must be >= 0")
        fields["cost_cents"] = body.cost_cents
    if body.price_cents is not None:
        if body.price_cents < 0:
            raise HTTPException(422, "price_cents must be >= 0")
        fields["price_cents"] = body.price_cents
    if len(fields) == 1:
        raise HTTPException(422, "Provide cost_cents and/or price_cents")

    await db.update("products", fields, filters={"id": f"eq.{product_id}"})
    dashboard_cache.invalidate_org(org_id)  # margins/products recompute on next read
    return {"ok": True, "product_id": product_id,
            "cost_cents": fields.get("cost_cents"), "price_cents": fields.get("price_cents")}


# ─── Insights ─────────────────────────────────────────────

@router.get("/insights")
async def get_insights(
    org_id: OrgId,
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by action_status"),
    db=Depends(_get_db),
):
    """Active AI-generated insights."""
    cache_key = dashboard_cache.make_key("insights", org_id, limit=limit, status=status)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

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

    result = {
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
    dashboard_cache.set(cache_key, result, TTL_SLOW)
    return result


@router.patch("/insights/{insight_id}/action")
async def update_insight_action(
    insight_id: str,
    action_status: str = Query(..., description="New status: viewed, accepted, dismissed, completed"),
    org_id: OrgId = None,
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


@router.get("/insights/cooldown")
async def get_insights_cooldown(
    org_id: OrgId = None,
    db=Depends(_get_db),
):
    """Check if insight generation is still cooling down (2hr window)."""
    COOLDOWN_HOURS = 2

    # Check the most recent insight's created_at for this org
    recent = await db.select(
        "insights",
        filters={"org_id": f"eq.{org_id}", "is_active": "eq.true"},
        order="created_at.desc",
        limit=1,
    )

    if not recent:
        return {"cooling_down": False, "seconds_remaining": 0, "ready_at": None}

    last_generated = datetime.fromisoformat(
        recent[0]["created_at"].replace("Z", "+00:00")
    )
    ready_at = last_generated + timedelta(hours=COOLDOWN_HOURS)
    now = datetime.now(timezone.utc)

    if now >= ready_at:
        return {
            "cooling_down": False,
            "seconds_remaining": 0,
            "ready_at": ready_at.isoformat(),
        }

    remaining = int((ready_at - now).total_seconds())
    return {
        "cooling_down": True,
        "seconds_remaining": remaining,
        "ready_at": ready_at.isoformat(),
    }


# ─── Forecasts ────────────────────────────────────────────

@router.get("/forecasts")
async def get_forecasts(
    org_id: OrgId,
    forecast_type: Optional[str] = Query(None, description="daily_revenue, weekly_revenue, product_demand"),
    db=Depends(_get_db),
):
    """Revenue forecasts."""
    cache_key = dashboard_cache.make_key("forecasts", org_id, forecast_type=forecast_type)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

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

    result = {
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
    dashboard_cache.set(cache_key, result, TTL_SLOW)
    return result


# ─── Notifications ────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(
    org_id: OrgId,
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db=Depends(_get_db),
):
    """User notifications (in-app).

    Narrow exception handling: SupabaseRESTError with status 401/403/404 (the
    genuine "RLS-denied / not-found / unknown-table" patterns from PostgREST)
    is converted to a graceful HTTP 404 so the customer-Layout notifications
    poller doesn't fill DevTools with red 500s on every admin page mount.

    Any other failure (PostgREST 400 from a malformed query, 5xx upstream,
    network timeout, unhandled bug) is re-raised so it surfaces as a real
    500 — observability isn't laundered into a calm 404.
    """
    filters: dict = {
        "org_id": f"eq.{org_id}",
    }
    if unread_only:
        filters["acknowledged_at"] = "is.null"

    try:
        notifications = await db.select(
            "notifications",
            filters=filters,
            order="created_at.desc",
            limit=limit,
        )
    except SupabaseRESTError as exc:
        # Only the genuine not-found / RLS-denied PostgREST responses become
        # graceful 404s. Validation 400s and upstream 5xx propagate.
        if exc.status_code in (401, 403, 404):
            logger.warning(
                "notifications fetch denied/missing for org_id=%s: "
                "status=%d message=%r details=%r",
                org_id, exc.status_code, exc.message, exc.details,
            )
            raise HTTPException(
                status_code=404,
                detail=(
                    "Notifications unavailable for this organization "
                    f"(store returned {exc.status_code})"
                ),
            )
        # Non-404-shaped errors: log full context, then re-raise so FastAPI
        # converts to the appropriate 5xx and we keep observability.
        logger.error(
            "notifications fetch failed with unexpected store error for "
            "org_id=%s: status=%d message=%r details=%r",
            org_id, exc.status_code, exc.message, exc.details,
        )
        raise

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


@router.post("/notifications/acknowledge")
async def acknowledge_notification(
    org_id: OrgId,
    notification_id: str = Query(..., description="Notification ID to acknowledge"),
    db=Depends(_get_db),
):
    """Mark a single notification as read."""
    if not _UUID_RE.match(notification_id):
        raise HTTPException(400, "Invalid notification_id format")
    now = datetime.now(timezone.utc).isoformat()
    await db.update(
        "notifications",
        {"acknowledged_at": now},
        filters={"id": f"eq.{notification_id}", "org_id": f"eq.{org_id}"},
    )
    return {"ok": True, "notification_id": notification_id}


@router.post("/notifications/acknowledge-all")
async def acknowledge_all_notifications(
    org_id: OrgId,
    db=Depends(_get_db),
):
    """Mark all unread notifications as read for an org."""
    now = datetime.now(timezone.utc).isoformat()
    await db.update(
        "notifications",
        {"acknowledged_at": now},
        filters={"org_id": f"eq.{org_id}", "acknowledged_at": "is.null"},
    )
    return {"ok": True}


# ─── Connection Status ───────────────────────────────────

@router.get("/connection")
async def get_connection(
    org_id: OrgId = None,
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
                "external_merchant_id": r.get("external_merchant_id"),
                "external_location_id": r.get("external_location_id"),
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
    org_id: OrgId = None,
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


# ─── Transaction Drill-Down ──────────────────────────────

@router.get("/transactions/day")
async def get_day_transactions(
    org_id: OrgId,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db=Depends(_get_db),
):
    """
    Get individual transactions for a specific day.
    Returns line-item-level detail for drill-down analysis.
    """
    transactions = await db.select(
        "transactions",
        filters={
            "org_id": f"eq.{org_id}",
            # Use transaction_at (when the sale happened), NOT created_at (row
            # insert time) — backfilled historical sales all get a recent
            # created_at, so filtering on it hid every drilled-into day.
            "transaction_at": f"gte.{date}T00:00:00Z",
        },
        order="transaction_at.asc",
        limit=500,
    )

    # Filter to same-day only (Supabase gte doesn't have lte in same filter easily)
    day_txns = [
        t for t in transactions
        if t.get("transaction_at", "")[:10] == date
    ]

    # Load line items for each transaction
    tx_ids = [t["id"] for t in day_txns if t.get("id")]
    line_items_by_tx: dict[str, list] = {}

    if tx_ids:
        # Batch fetch line items with one in.() query per chunk
        # (chunked to keep the PostgREST query string a safe length)
        for i in range(0, len(tx_ids), 100):
            chunk = tx_ids[i : i + 100]
            items = await db.select(
                "transaction_line_items",
                filters={
                    "transaction_id": f"in.({','.join(chunk)})",
                },
            )
            for item in items:
                line_items_by_tx.setdefault(item.get("transaction_id"), []).append(item)

    # Build response
    result_txns = []
    product_qty: dict[str, int] = {}

    for t in day_txns:
        tx_id = t.get("id", "")
        items = line_items_by_tx.get(tx_id, [])

        formatted_items = []
        for item in items:
            qty = item.get("quantity", 1) or 1
            name = item.get("product_name", "Unknown")
            product_qty[name] = product_qty.get(name, 0) + qty
            formatted_items.append({
                "id": item.get("id", ""),
                "product_name": name,
                "sku": item.get("sku"),
                "quantity": qty,
                "unit_price_cents": item.get("unit_price_cents", 0),
                "total_cents": item.get("total_cents", 0),
                "category": item.get("category"),
            })

        result_txns.append({
            "id": tx_id,
            "created_at": t.get("transaction_at", ""),
            "total_cents": t.get("total_cents", 0) or 0,
            "tip_cents": t.get("tip_cents", 0) or 0,
            "discount_cents": t.get("discount_cents", 0) or 0,
            "refund_cents": t.get("refund_cents", 0) or 0,
            "payment_method": t.get("payment_method", "unknown"),
            "items": formatted_items,
        })

    total_revenue = sum(t["total_cents"] for t in result_txns)
    unique_products = len(product_qty)
    top_product = max(product_qty, key=product_qty.get, default="") if product_qty else ""
    top_qty = product_qty.get(top_product, 0)

    return {
        "date": date,
        "transactions": result_txns,
        "summary": {
            "total_revenue_cents": total_revenue,
            "transaction_count": len(result_txns),
            "unique_products": unique_products,
            "avg_ticket_cents": total_revenue // len(result_txns) if result_txns else 0,
            "top_product": top_product,
            "top_product_qty": top_qty,
        },
    }


# ─── Inventory ────────────────────────────────────────────

@router.get("/inventory")
async def get_inventory(
    org_id: OrgId = None,
    db=Depends(_get_db),
):
    """Current inventory levels with reorder predictions."""
    try:
        inventory = await db.get_inventory_current(org_id)
    except Exception:
        return {"items": [], "total": 0, "alerts": {"low_stock": 0, "overstocked": 0, "trending_up": 0}}

    items = []
    low_stock = 0
    overstocked = 0
    trending_up = 0

    for item in inventory:
        daily_usage = item.get("predicted_daily_usage", 0) or 0
        current = item.get("current_stock", 0) or 0
        reorder = item.get("reorder_point", 0) or 0
        trend = item.get("trend", "stable")

        days_until = None
        if daily_usage > 0:
            days_until = max(0, int((current - reorder) / daily_usage))

        if days_until is not None and days_until <= 2:
            low_stock += 1
        if daily_usage > 0 and current > daily_usage * 12:
            overstocked += 1
        if trend == "rising":
            trending_up += 1

        items.append({
            "id": item.get("id", ""),
            "product_name": item.get("product_name", ""),
            "sku": item.get("sku", ""),
            "category": item.get("category", ""),
            "current_stock": current,
            "unit": item.get("unit", "units"),
            "reorder_point": reorder,
            "predicted_daily_usage": daily_usage,
            "days_until_reorder": days_until,
            "trend": trend,
            "trend_pct": item.get("trend_pct", 0) or 0,
            "last_updated": item.get("last_updated", ""),
        })

    return {
        "items": items,
        "total": len(items),
        "alerts": {
            "low_stock": low_stock,
            "overstocked": overstocked,
            "trending_up": trending_up,
        },
    }



# ─── Trends ──────────────────────────────────────────────

@router.get("/trends")
async def get_trends(
    org_id: OrgId,
    days: int = Query(30, ge=7, le=90),
    db=Depends(_get_db),
):
    """Revenue trends: week-over-week and day-over-day changes."""
    cache_key = dashboard_cache.make_key("trends", org_id, days=days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    daily = await db.get_daily_revenue(org_id, days=days)

    now = datetime.now(timezone.utc)
    mid = (now - timedelta(days=days // 2)).isoformat()

    recent = [r for r in daily if r.get("day_bucket", "") >= mid]
    earlier = [r for r in daily if r.get("day_bucket", "") < mid]

    recent_rev = sum(r.get("total_revenue_cents", 0) or 0 for r in recent)
    earlier_rev = sum(r.get("total_revenue_cents", 0) or 0 for r in earlier)
    recent_txns = sum(r.get("transaction_count", 0) or 0 for r in recent)
    earlier_txns = sum(r.get("transaction_count", 0) or 0 for r in earlier)

    rev_change = round((recent_rev - earlier_rev) / earlier_rev * 100, 1) if earlier_rev else 0
    txn_change = round((recent_txns - earlier_txns) / earlier_txns * 100, 1) if earlier_txns else 0

    daily_trends = []
    for i, day in enumerate(daily):
        prev_rev = daily[i - 1].get("total_revenue_cents", 0) or 0 if i > 0 else 0
        curr_rev = day.get("total_revenue_cents", 0) or 0
        change = round((curr_rev - prev_rev) / prev_rev * 100, 1) if prev_rev else 0
        daily_trends.append({
            "date": day.get("day_bucket"),
            "revenue_cents": curr_rev,
            "transactions": day.get("transaction_count", 0) or 0,
            "change_pct": change,
        })

    result = {
        "period_days": days,
        "revenue_change_pct": rev_change,
        "transaction_change_pct": txn_change,
        "recent_revenue_cents": recent_rev,
        "earlier_revenue_cents": earlier_rev,
        "daily": daily_trends,
    }
    dashboard_cache.set(cache_key, result, TTL_FAST)
    return result


# ─── Cache Management ───────────────────────────────────

@router.post("/burn-rate/send", dependencies=[Depends(require_admin)])
async def trigger_burn_rate_sms():
    """Manually trigger daily burn rate SMS. Admin only."""
    from ...analytics.burn_rate import send_burn_rate_sms

    result = await send_burn_rate_sms()
    return result


@router.post("/cache/flush", dependencies=[Depends(require_admin)])
async def flush_cache(
    org_id: OrgId,
):
    """Flush dashboard cache for an organization."""
    dashboard_cache.invalidate_org(org_id)
    return {"flushed": True, "org_id": org_id}
