"""
Dashboard Analytics API Routes — Extended analytics for Meridian frontend.

Endpoints:
  GET /api/dashboard/staff           → Staff performance (revenue, txns, avg ticket)
  GET /api/dashboard/margins         → Product margin analysis
  GET /api/dashboard/menu-engineering → BCG matrix (stars, plowhorses, puzzles, dogs)
  GET /api/dashboard/anomalies       → Revenue anomaly detection (z-score)
  GET /api/dashboard/customers       → Customer analytics summary
  GET /api/dashboard/agents          → AI agent swarm status
  GET /api/dashboard/actions         → Prioritized action list from insights
"""
import asyncio
import logging
import math
import re
from typing import Annotated

from fastapi import APIRouter, Query, HTTPException, Depends

from ..auth import require_org_access
from ...db.cache import dashboard_cache, TTL_FAST, TTL_SLOW
from ...db.revenue import is_revenue_txn, net_revenue_cents

logger = logging.getLogger("meridian.api.analytics")

# Router-level tenancy guard: every endpoint that accepts org_id (query or path)
# is automatically protected. See require_org_access in ../auth.py.
router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard-analytics"],
    dependencies=[Depends(require_org_access)],
)

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)
def _validate_org_id(org_id: str = Query(..., description="Organization ID")) -> str:
    if not _UUID_RE.match(org_id) and not org_id.startswith('biz_'):
        raise HTTPException(422, "org_id must be a valid UUID or business ID")
    return org_id


OrgId = Annotated[str, Depends(_validate_org_id)]

# Typical cost-of-goods ratio by business type, used ONLY to estimate margins
# before a merchant supplies real costs. Rough industry ballparks — always shown
# as "estimated" and replaced the moment a real cost is entered/uploaded.
_COGS_BY_VERTICAL = {
    "restaurant": 0.32, "cafe": 0.28, "coffee_shop": 0.28, "coffee": 0.28,
    "bar": 0.22, "bakery": 0.30, "food_truck": 0.33, "quick_service": 0.30,
    "retail": 0.55, "grocery": 0.68, "convenience": 0.70, "boutique": 0.50,
    "salon": 0.15, "spa": 0.15, "fitness": 0.12, "service": 0.10, "other": 0.40,
}
_DEFAULT_COGS_PCT = 0.40


def _get_db():
    from ...db import _db_instance
    if _db_instance is None:
        raise HTTPException(503, "Database not initialized")
    return _db_instance


# ─── Staff Performance ──────────────────────────────────────

@router.get("/staff")
async def get_staff_performance(
    org_id: OrgId,
    days: int = Query(30, ge=7, le=365),
    db=Depends(_get_db),
):
    """
    Staff performance metrics derived from transaction employee data.
    Aggregates revenue, transaction count, and average ticket per employee.
    """
    cache_key = dashboard_cache.make_key("staff", org_id, days=days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        transactions = await db.get_recent_transactions(org_id, days=days)
    except Exception as e:
        logger.error(f"Failed to load transactions for staff analytics: {e}")
        return {"staff": [], "total_staff": 0, "period_days": days}

    # Aggregate by employee_name
    staff_map: dict[str, dict] = {}
    for txn in transactions:
        # Revenue is completed sales only — skip voids and net refunds (audit #6).
        if not is_revenue_txn(txn):
            continue
        name = txn.get("employee_name") or "Unknown"
        if name not in staff_map:
            staff_map[name] = {
                "name": name,
                "revenue_cents": 0,
                "transaction_count": 0,
                "tip_cents": 0,
                "refund_cents": 0,
            }
        entry = staff_map[name]
        refund = txn.get("refund_cents", 0) or 0
        entry["revenue_cents"] += (txn.get("total_cents", 0) or 0) - refund
        entry["transaction_count"] += 1
        entry["tip_cents"] += txn.get("tip_cents", 0) or 0
        entry["refund_cents"] += refund

    staff_list = []
    for name, data in staff_map.items():
        count = data["transaction_count"]
        avg_ticket = data["revenue_cents"] // count if count > 0 else 0
        staff_list.append({
            "name": name,
            "revenue_cents": data["revenue_cents"],
            "transaction_count": count,
            "avg_ticket_cents": avg_ticket,
            "tip_cents": data["tip_cents"],
            "refund_cents": data["refund_cents"],
        })

    # Sort by revenue descending
    staff_list.sort(key=lambda x: x["revenue_cents"], reverse=True)

    result = {
        "staff": staff_list,
        "total_staff": len(staff_list),
        "period_days": days,
    }
    dashboard_cache.set(cache_key, result, TTL_FAST)
    return result


# ─── Margin Analysis ────────────────────────────────────────

@router.get("/margins")
async def get_margins(
    org_id: OrgId,
    days: int = Query(30, ge=7, le=365),
    db=Depends(_get_db),
):
    """
    Product margin analysis.
    Joins product cost data with transaction item revenue to compute margins.
    """
    cache_key = dashboard_cache.make_key("margins", org_id, days=days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        products, performance = await asyncio.gather(
            db.get_products(org_id),
            db.get_product_performance(org_id, days=days),
        )
    except Exception as e:
        logger.error(f"Failed to load data for margin analytics: {e}")
        return {"products": [], "summary": {}, "period_days": days}

    # Build product info map (includes cost_per_unit if available)
    product_map = {p["id"]: p for p in products}

    # Aggregate performance by product
    perf_agg: dict[str, dict] = {}
    for row in performance:
        pid = row.get("product_id")
        if pid not in perf_agg:
            perf_agg[pid] = {
                "product_id": pid,
                "total_revenue_cents": 0,
                "total_quantity": 0,
            }
        agg = perf_agg[pid]
        agg["total_revenue_cents"] += row.get("total_revenue_cents", 0) or 0
        agg["total_quantity"] += row.get("total_quantity", 0) or 0

    # Estimated-margin fallback: when a product has no real cost yet, estimate
    # cost-of-goods from a typical COGS ratio for the business type so the page
    # isn't empty. Each item is flagged is_estimated; a real cost (entered or
    # uploaded) replaces the estimate immediately.
    vertical = ""
    try:
        org_rows = await db.select("organizations", filters={"id": f"eq.{org_id}"}, limit=1)
        vertical = (org_rows[0].get("vertical") or "").lower() if org_rows else ""
    except Exception:
        vertical = ""
    est_cogs = _COGS_BY_VERTICAL.get(vertical, _DEFAULT_COGS_PCT)

    margin_items = []
    total_revenue = 0
    total_cost = 0
    estimated_count = 0

    for pid, perf in perf_agg.items():
        product = product_map.get(pid, {})
        name = product.get("name", "Unknown")
        category_id = product.get("category_id")
        # Per-unit cost of goods, in cents. Column is `cost_cents` (was reading
        # the non-existent `cost_per_unit`, so cost was always 0 → fake 100%
        # margins). Null until a cost sheet / restock invoice is uploaded — then
        # we fall back to a vertical-based estimate, clearly flagged.
        cost_per_unit = product.get("cost_cents") or 0
        revenue = perf["total_revenue_cents"]
        quantity = perf["total_quantity"]
        if cost_per_unit > 0:
            cost = cost_per_unit * quantity
            estimated = False
        else:
            cost = int(round(revenue * est_cogs))
            estimated = True
            estimated_count += 1

        margin_pct = 0.0
        if revenue > 0:
            margin_pct = round((revenue - cost) / revenue * 100, 1)

        total_revenue += revenue
        total_cost += cost

        margin_items.append({
            "product_id": pid,
            "name": name,
            "category_id": category_id,
            "revenue_cents": revenue,
            "cost_cents": int(cost),
            "profit_cents": revenue - int(cost),
            "margin_pct": margin_pct,
            "quantity_sold": quantity,
            "is_estimated": estimated,
            "cost_source": "estimated" if estimated else "actual",
        })

    # Sort by profit descending
    margin_items.sort(key=lambda x: x["profit_cents"], reverse=True)

    overall_margin = 0.0
    if total_revenue > 0:
        overall_margin = round((total_revenue - total_cost) / total_revenue * 100, 1)

    # Catalog-wide cost coverage drives the "upload a cost sheet" prompt — count
    # over ALL active products, not just those that sold in the window.
    catalog_total = len(products)
    catalog_with_cost = sum(1 for p in products if (p.get("cost_cents") or 0) > 0)

    result = {
        "products": margin_items,
        "summary": {
            "total_revenue_cents": total_revenue,
            "total_cost_cents": int(total_cost),
            "total_profit_cents": total_revenue - int(total_cost),
            "overall_margin_pct": overall_margin,
            "products_with_cost": sum(1 for m in margin_items if m["cost_cents"] > 0),
            "products_without_cost": sum(1 for m in margin_items if m["cost_cents"] == 0),
            "catalog_total": catalog_total,
            "catalog_with_cost": catalog_with_cost,
            "catalog_missing_cost": catalog_total - catalog_with_cost,
            "estimated_items": estimated_count,
            "has_estimates": estimated_count > 0,
            "est_cogs_pct": round(est_cogs * 100),
        },
        "period_days": days,
    }
    dashboard_cache.set(cache_key, result, TTL_FAST)
    return result


# ─── Menu Engineering (BCG Matrix) ──────────────────────────

@router.get("/menu-engineering")
async def get_menu_engineering(
    org_id: OrgId,
    days: int = Query(30, ge=7, le=365),
    db=Depends(_get_db),
):
    """
    BCG-style menu engineering matrix.
    Classifies items into Stars, Plowhorses, Puzzles, and Dogs
    based on popularity (quantity sold) and profitability (margin %).
    """
    cache_key = dashboard_cache.make_key("menu_eng", org_id, days=days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        products, performance = await asyncio.gather(
            db.get_products(org_id),
            db.get_product_performance(org_id, days=days),
        )
    except Exception as e:
        logger.error(f"Failed to load data for menu engineering: {e}")
        return {"items": [], "quadrants": {}, "period_days": days}

    product_map = {p["id"]: p for p in products}

    # Aggregate per product
    perf_agg: dict[str, dict] = {}
    for row in performance:
        pid = row.get("product_id")
        if pid not in perf_agg:
            perf_agg[pid] = {
                "product_id": pid,
                "total_revenue_cents": 0,
                "total_quantity": 0,
            }
        agg = perf_agg[pid]
        agg["total_revenue_cents"] += row.get("total_revenue_cents", 0) or 0
        agg["total_quantity"] += row.get("total_quantity", 0) or 0

    if not perf_agg:
        result = {"items": [], "quadrants": {"stars": 0, "plowhorses": 0, "puzzles": 0, "dogs": 0}, "period_days": days}
        dashboard_cache.set(cache_key, result, TTL_FAST)
        return result

    # Compute margin for each product
    items = []
    for pid, perf in perf_agg.items():
        product = product_map.get(pid, {})
        # Real column is `cost_cents` (was reading non-existent `cost_per_unit`
        # → cost always 0 → every item fake-100% margin → bogus BCG split).
        cost_per_unit = product.get("cost_cents") or 0
        revenue = perf["total_revenue_cents"]
        quantity = perf["total_quantity"]
        cost = cost_per_unit * quantity

        margin_pct = 0.0
        if revenue > 0:
            margin_pct = (revenue - cost) / revenue * 100

        items.append({
            "product_id": pid,
            "name": product.get("name", "Unknown"),
            "category_id": product.get("category_id"),
            "revenue_cents": revenue,
            "quantity_sold": quantity,
            "margin_pct": round(margin_pct, 1),
            "cost_cents": int(cost),
        })

    # Calculate medians for thresholds
    quantities = sorted(i["quantity_sold"] for i in items)
    margins = sorted(i["margin_pct"] for i in items)

    mid = len(quantities) // 2
    median_qty = quantities[mid] if quantities else 0
    median_margin = margins[mid] if margins else 0.0

    # Classify into quadrants
    quadrant_counts = {"stars": 0, "plowhorses": 0, "puzzles": 0, "dogs": 0}
    for item in items:
        high_pop = item["quantity_sold"] >= median_qty
        high_margin = item["margin_pct"] >= median_margin

        if high_pop and high_margin:
            item["quadrant"] = "star"
            quadrant_counts["stars"] += 1
        elif high_pop and not high_margin:
            item["quadrant"] = "plowhorse"
            quadrant_counts["plowhorses"] += 1
        elif not high_pop and high_margin:
            item["quadrant"] = "puzzle"
            quadrant_counts["puzzles"] += 1
        else:
            item["quadrant"] = "dog"
            quadrant_counts["dogs"] += 1

    # Sort: stars first, then by revenue
    quadrant_order = {"star": 0, "plowhorse": 1, "puzzle": 2, "dog": 3}
    items.sort(key=lambda x: (quadrant_order.get(x["quadrant"], 9), -x["revenue_cents"]))

    result = {
        "items": items,
        "quadrants": quadrant_counts,
        "thresholds": {
            "median_quantity": median_qty,
            "median_margin_pct": round(median_margin, 1),
        },
        "period_days": days,
    }
    dashboard_cache.set(cache_key, result, TTL_FAST)
    return result


# ─── Anomaly Detection ──────────────────────────────────────

@router.get("/anomalies")
async def get_anomalies(
    org_id: OrgId,
    days: int = Query(30, ge=14, le=90),
    threshold: float = Query(2.0, ge=1.0, le=4.0, description="Z-score threshold"),
    db=Depends(_get_db),
):
    """
    Revenue anomaly detection using z-scores.
    Flags days where revenue deviates significantly from the mean.
    Also checks for unusual refund/void patterns.
    """
    cache_key = dashboard_cache.make_key("anomalies", org_id, days=days, threshold=threshold)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        daily = await db.get_daily_revenue(org_id, days=days)
    except Exception as e:
        logger.error(f"Failed to load daily revenue for anomaly detection: {e}")
        return {"anomalies": [], "total": 0, "period_days": days}

    if len(daily) < 3:
        result = {"anomalies": [], "total": 0, "period_days": days, "note": "Insufficient data (need 3+ days)"}
        dashboard_cache.set(cache_key, result, TTL_SLOW)
        return result

    # Compute mean and std dev for revenue
    revenues = [r.get("total_revenue_cents", 0) or 0 for r in daily]
    txn_counts = [r.get("transaction_count", 0) or 0 for r in daily]
    refund_totals = [r.get("refund_total_cents", 0) or 0 for r in daily]

    mean_rev = sum(revenues) / len(revenues)
    variance = sum((r - mean_rev) ** 2 for r in revenues) / len(revenues)
    std_dev = math.sqrt(variance) if variance > 0 else 0

    mean_txn = sum(txn_counts) / len(txn_counts) if txn_counts else 0
    txn_variance = sum((t - mean_txn) ** 2 for t in txn_counts) / len(txn_counts) if txn_counts else 0
    txn_std = math.sqrt(txn_variance) if txn_variance > 0 else 0

    mean_refund = sum(refund_totals) / len(refund_totals) if refund_totals else 0
    refund_variance = sum((r - mean_refund) ** 2 for r in refund_totals) / len(refund_totals) if refund_totals else 0
    refund_std = math.sqrt(refund_variance) if refund_variance > 0 else 0

    anomalies = []

    for i, row in enumerate(daily):
        date = row.get("day_bucket", "")
        rev = revenues[i]
        txns = txn_counts[i]
        refunds = refund_totals[i]

        # Revenue anomaly
        if std_dev > 0:
            z_score = (rev - mean_rev) / std_dev
            if abs(z_score) > threshold:
                direction = "spike" if z_score > 0 else "drop"
                anomalies.append({
                    "type": f"revenue_{direction}",
                    "date": date,
                    "z_score": round(z_score, 2),
                    "magnitude": abs(round(z_score, 2)),
                    "value_cents": rev,
                    "expected_cents": int(mean_rev),
                    "description": (
                        f"Revenue {'spike' if z_score > 0 else 'drop'}: "
                        f"${rev / 100:,.0f} vs avg ${mean_rev / 100:,.0f} "
                        f"({abs(z_score):.1f} standard deviations)"
                    ),
                })

        # Refund anomaly
        if refund_std > 0 and mean_refund > 0:
            refund_z = (refunds - mean_refund) / refund_std
            if refund_z > threshold:
                anomalies.append({
                    "type": "refund_spike",
                    "date": date,
                    "z_score": round(refund_z, 2),
                    "magnitude": abs(round(refund_z, 2)),
                    "value_cents": refunds,
                    "expected_cents": int(mean_refund),
                    "description": (
                        f"Unusually high refunds: ${refunds / 100:,.0f} "
                        f"vs avg ${mean_refund / 100:,.0f}"
                    ),
                })

        # Transaction count anomaly
        if txn_std > 0:
            txn_z = (txns - mean_txn) / txn_std
            if abs(txn_z) > threshold:
                direction = "spike" if txn_z > 0 else "drop"
                anomalies.append({
                    "type": f"transaction_{direction}",
                    "date": date,
                    "z_score": round(txn_z, 2),
                    "magnitude": abs(round(txn_z, 2)),
                    "value": txns,
                    "expected": int(mean_txn),
                    "description": (
                        f"Transaction count {direction}: "
                        f"{txns} vs avg {mean_txn:.0f}"
                    ),
                })

    # Sort by magnitude descending
    anomalies.sort(key=lambda x: x["magnitude"], reverse=True)

    result = {
        "anomalies": anomalies,
        "total": len(anomalies),
        "stats": {
            "mean_revenue_cents": int(mean_rev),
            "std_dev_cents": int(std_dev),
            "mean_transactions": round(mean_txn, 1),
            "threshold": threshold,
        },
        "period_days": days,
    }
    dashboard_cache.set(cache_key, result, TTL_SLOW)
    return result


# ─── Customer Analytics ─────────────────────────────────────

@router.get("/customers")
async def get_customers(
    org_id: OrgId,
    days: int = Query(30, ge=7, le=365),
    db=Depends(_get_db),
):
    """
    Customer analytics derived from transaction data.
    Groups by payment method patterns and available customer identifiers.
    """
    cache_key = dashboard_cache.make_key("customers", org_id, days=days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        daily = await db.get_daily_revenue(org_id, days=days)
        transactions = await db.get_recent_transactions(org_id, days=days)
    except Exception as e:
        logger.error(f"Failed to load data for customer analytics: {e}")
        return {"summary": {}, "payment_methods": [], "top_customers": [], "period_days": days}

    # Total unique customers from daily aggregates (if tracked)
    total_customers_from_daily = sum(
        r.get("unique_customers", 0) or 0 for r in daily
    )

    # Analyze by payment method
    method_map: dict[str, dict] = {}
    customer_map: dict[str, dict] = {}

    for txn in transactions:
        # Net sales only — skip voids, subtract refunds (audit #6).
        if not is_revenue_txn(txn):
            continue
        method = txn.get("payment_method", "unknown") or "unknown"
        total = (txn.get("total_cents", 0) or 0) - (txn.get("refund_cents", 0) or 0)

        if method not in method_map:
            method_map[method] = {
                "method": method,
                "transaction_count": 0,
                "revenue_cents": 0,
            }
        method_map[method]["transaction_count"] += 1
        method_map[method]["revenue_cents"] += total

        # Group by customer identifier if available (external customer_id in metadata)
        meta = txn.get("metadata") or {}
        cust_id = meta.get("customer_id") or meta.get("customer_email")
        if cust_id:
            if cust_id not in customer_map:
                customer_map[cust_id] = {
                    "customer_id": cust_id,
                    "transaction_count": 0,
                    "total_spent_cents": 0,
                    "first_seen": txn.get("transaction_at", ""),
                    "last_seen": txn.get("transaction_at", ""),
                }
            c = customer_map[cust_id]
            c["transaction_count"] += 1
            c["total_spent_cents"] += total
            txn_time = txn.get("transaction_at", "")
            if txn_time > c["last_seen"]:
                c["last_seen"] = txn_time
            if txn_time < c["first_seen"]:
                c["first_seen"] = txn_time

    # Payment method breakdown
    payment_methods = sorted(
        method_map.values(), key=lambda x: x["revenue_cents"], reverse=True
    )

    # Completed sales only; net revenue (excludes voids, nets refunds — audit #6).
    total_txns = sum(1 for t in transactions if is_revenue_txn(t))
    total_revenue = net_revenue_cents(transactions)
    avg_ticket = total_revenue // total_txns if total_txns else 0

    # Customer segments from identified customers
    identified = list(customer_map.values())
    repeat_customers = [c for c in identified if c["transaction_count"] > 1]
    repeat_rate = len(repeat_customers) / len(identified) * 100 if identified else 0

    # Top customers by spend
    top_customers = sorted(identified, key=lambda x: x["total_spent_cents"], reverse=True)[:20]

    result = {
        "summary": {
            "total_transactions": total_txns,
            "total_revenue_cents": total_revenue,
            "avg_ticket_cents": avg_ticket,
            "unique_customers_estimated": total_customers_from_daily or len(identified) or total_txns,
            "identified_customers": len(identified),
            "repeat_customers": len(repeat_customers),
            "repeat_rate_pct": round(repeat_rate, 1),
        },
        "payment_methods": payment_methods,
        "top_customers": top_customers,
        "period_days": days,
    }
    dashboard_cache.set(cache_key, result, TTL_SLOW)
    return result


# ─── AI Agent Status ────────────────────────────────────────

@router.get("/agents")
async def get_agents(
    org_id: OrgId,
    db=Depends(_get_db),
):
    """
    AI agent swarm status: lists active agents with scorecards and latest findings.
    Combines swarm trainer scorecards with recent insights per agent type.
    """
    cache_key = dashboard_cache.make_key("agents", org_id)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    # Get agent scorecards from swarm trainer
    scorecards = {}
    try:
        from ...ai.swarm_trainer import get_swarm_trainer
        trainer = get_swarm_trainer()
        scorecards = trainer.get_scorecards()
    except Exception as e:
        logger.warning(f"Could not load swarm trainer scorecards: {e}")

    # Get recent insights to see which agents produced findings
    recent_insights = []
    try:
        recent_insights = await db.select(
            "insights",
            filters={
                "org_id": f"eq.{org_id}",
                "is_active": "eq.true",
            },
            order="created_at.desc",
            limit=50,
        )
    except Exception as e:
        logger.warning(f"Could not load recent insights for agent status: {e}")

    # Map insights to agent types
    insights_by_type: dict[str, list] = {}
    for ins in recent_insights:
        agent_type = ins.get("type", "unknown")
        if agent_type not in insights_by_type:
            insights_by_type[agent_type] = []
        if len(insights_by_type[agent_type]) < 3:  # Keep top 3 per type
            insights_by_type[agent_type].append({
                "id": ins.get("id"),
                "title": ins.get("title"),
                "confidence": ins.get("confidence_score"),
                "impact_cents": ins.get("estimated_monthly_impact_cents"),
                "created_at": ins.get("created_at"),
            })

    # Build agent list from scorecards + insight types
    agent_names = set(scorecards.keys()) | set(insights_by_type.keys())
    agents = []

    for name in sorted(agent_names):
        card = scorecards.get(name, {})
        findings = insights_by_type.get(name, [])

        agents.append({
            "name": name,
            "total_runs": card.get("total_runs", 0),
            "avg_confidence": card.get("avg_confidence", 0.0),
            "accuracy_score": card.get("accuracy_score", 0.0),
            "engagement_rate": card.get("engagement_rate", 0.0),
            "trend": card.get("trend", "stable"),
            "last_trained": card.get("last_trained", ""),
            "pattern_count": card.get("pattern_count", 0),
            "recent_findings": findings,
            "status": "active" if card.get("total_runs", 0) > 0 or findings else "idle",
        })

    result = {
        "agents": agents,
        "total_agents": len(agents),
        "active_count": sum(1 for a in agents if a["status"] == "active"),
        "improving_count": sum(1 for a in agents if a["trend"] == "improving"),
    }
    dashboard_cache.set(cache_key, result, TTL_SLOW)
    return result


# ─── Prioritized Actions ────────────────────────────────────

@router.get("/actions")
async def get_actions(
    org_id: OrgId,
    limit: int = Query(20, ge=1, le=100),
    db=Depends(_get_db),
):
    """
    Prioritized action list derived from AI insights.
    Sorted by estimated monthly impact (highest first).
    """
    cache_key = dashboard_cache.make_key("actions", org_id, limit=limit)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        insights = await db.select(
            "insights",
            filters={
                "org_id": f"eq.{org_id}",
                "is_active": "eq.true",
            },
            order="estimated_monthly_impact_cents.desc.nullslast",
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Failed to load insights for actions: {e}")
        return {"actions": [], "total": 0}

    actions = []
    total_impact = 0

    for ins in insights:
        impact = ins.get("estimated_monthly_impact_cents", 0) or 0
        total_impact += impact

        actions.append({
            "id": ins.get("id"),
            "type": ins.get("type"),
            "title": ins.get("title"),
            "summary": ins.get("summary"),
            "impact_cents": impact,
            "confidence": ins.get("confidence_score", 0),
            "action_status": ins.get("action_status", "pending"),
            "priority": _compute_priority(impact, ins.get("confidence_score", 0)),
            "valid_until": ins.get("valid_until"),
            "created_at": ins.get("created_at"),
        })

    result = {
        "actions": actions,
        "total": len(actions),
        "total_impact_cents": total_impact,
        "pending_count": sum(1 for a in actions if a["action_status"] in ("pending", None)),
        "accepted_count": sum(1 for a in actions if a["action_status"] == "accepted"),
        "completed_count": sum(1 for a in actions if a["action_status"] == "completed"),
    }
    dashboard_cache.set(cache_key, result, TTL_SLOW)
    return result


def _compute_priority(impact_cents: int, confidence: float) -> str:
    """Compute action priority based on impact and confidence."""
    score = (impact_cents / 100) * (confidence or 0.5)
    if score >= 500:
        return "critical"
    elif score >= 200:
        return "high"
    elif score >= 50:
        return "medium"
    return "low"
