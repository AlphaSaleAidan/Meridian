"""
Website Builder API routes — Merchant website creation, scraping, and management.

Endpoints:
  GET    /api/website/config                → Get merchant website config
  POST   /api/website/save                  → Create or update website config
  POST   /api/website/scrape                → Scrape business info from URL
  POST   /api/website/generate              → Generate AI copy for website
  POST   /api/website/publish               → Publish merchant website
  POST   /api/website/unpublish             → Unpublish merchant website
  GET    /api/website/public/{slug}         → Public website data (no auth)
  POST   /api/website/analytics             → Record analytics event (no auth)
  GET    /api/website/analytics/{merchant_id} → Analytics summary
  POST   /api/website/order                 → Create order from website (no auth)
  GET    /api/website/orders/{merchant_id}  → List merchant orders
  DELETE /api/website/{merchant_id}         → Soft-delete merchant website
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from ..auth import rate_limit_scrape
from pydantic import BaseModel

from ...db import get_db

import re

logger = logging.getLogger("meridian.api.website")

router = APIRouter(prefix="/api/website", tags=["website"])

_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


# ── Request/Response Models ───────────────────────────────────


class WebsiteConfigRequest(BaseModel):
    merchant_id: str
    portal_context: str | None = None
    slug: str | None = None
    business_name: str | None = None
    business_type: str | None = None
    tagline: str | None = None
    description: str | None = None
    template_id: str | None = None
    template_config: dict | None = None
    logo_url: str | None = None
    hero_headline: str | None = None
    hero_subheadline: str | None = None
    about_text: str | None = None
    services: list | None = None
    hours: dict | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    google_rating: float | None = None
    google_review_count: int | None = None
    google_reviews: list | None = None
    social_links: dict | None = None
    source_url: str | None = None
    google_place_id: str | None = None
    ordering_enabled: bool | None = None
    ordering_fee_pct: float | None = None
    stripe_connect_id: str | None = None


class ScrapeRequest(BaseModel):
    url: str
    merchant_id: str


class GenerateRequest(BaseModel):
    merchant_id: str


class PublishRequest(BaseModel):
    merchant_id: str


class UnpublishRequest(BaseModel):
    merchant_id: str


class AnalyticsEventRequest(BaseModel):
    website_id: str
    merchant_id: str
    event_type: str
    path: str | None = None
    referrer: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    device_type: str | None = None
    country: str | None = None
    city: str | None = None
    duration_seconds: int | None = None


class OrderItem(BaseModel):
    name: str
    quantity: int = 1
    price: float = 0.0


class CreateOrderRequest(BaseModel):
    website_id: str
    customer_name: str
    customer_phone: str | None = None
    customer_email: str | None = None
    order_type: str = "pickup"
    items: list[dict]


# ── Route Handlers ────────────────────────────────────────────


@router.get("/config")
async def get_website_config(merchant_id: str = Query(...)):
    """
    Return the merchant's website configuration.
    If no record exists, returns {exists: false}.
    """
    if not _UUID_RE.match(merchant_id):
        return {"exists": False, "merchant_id": merchant_id}

    db = get_db()

    rows = await db.select(
        "merchant_websites",
        filters={"merchant_id": f"eq.{merchant_id}"},
        limit=1,
    )

    if not rows:
        return {"exists": False, "merchant_id": merchant_id}

    return {"exists": True, **rows[0]}


@router.post("/save")
async def save_website_config(req: WebsiteConfigRequest):
    """
    Create or update a merchant_websites record.
    Auto-generates a slug from business_name if not provided.
    """
    from ...services.website_scraper import generate_slug

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Check for existing record
    existing = await db.select(
        "merchant_websites",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )

    # Build data payload, excluding None values
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    data["updated_at"] = now

    # Auto-generate slug if missing
    if not data.get("slug") and data.get("business_name"):
        data["slug"] = generate_slug(data["business_name"])

    if existing:
        # Update existing record
        record_id = existing[0]["id"]
        await db.update(
            "merchant_websites",
            data,
            filters={"id": f"eq.{record_id}"},
        )
        logger.info(f"Updated website config for merchant {req.merchant_id}")
        return {"ok": True, "action": "updated", "id": record_id, "slug": data.get("slug") or existing[0].get("slug")}
    else:
        # Create new record
        data["id"] = str(uuid4())
        data["created_at"] = now
        result = await db.insert("merchant_websites", data)
        record_id = result[0]["id"] if result else data["id"]
        logger.info(f"Created website config for merchant {req.merchant_id}")
        return {"ok": True, "action": "created", "id": record_id, "slug": data.get("slug")}


@router.post("/scrape", dependencies=[Depends(rate_limit_scrape)])
async def scrape_merchant_website(req: ScrapeRequest):
    """
    Scrape a business website for structured info.
    Updates scrape_status on the merchant_websites record.
    """
    from ...services.website_scraper import scrape_website

    db = get_db()

    # Mark scrape in progress
    existing = await db.select(
        "merchant_websites",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )
    if existing:
        await db.update(
            "merchant_websites",
            {
                "scrape_status": "in_progress",
                "source_url": req.url,
            },
            filters={"id": f"eq.{existing[0]['id']}"},
        )

    try:
        scraped = await scrape_website(req.url)
    except Exception as e:
        logger.error(f"Scrape failed for {req.url}: {e}")
        if existing:
            await db.update(
                "merchant_websites",
                {"scrape_status": "failed"},
                filters={"id": f"eq.{existing[0]['id']}"},
            )
        raise HTTPException(502, f"Scrape failed: {str(e)}")

    if scraped.get("error"):
        if existing:
            await db.update(
                "merchant_websites",
                {"scrape_status": "failed"},
                filters={"id": f"eq.{existing[0]['id']}"},
            )
        raise HTTPException(502, f"Scrape error: {scraped['error']}")

    # Scrape Google reviews in parallel (no API key needed)
    from ...services.website_scraper import scrape_google_reviews
    business_name = scraped.get("business_name", "")
    address = scraped.get("address", "")
    if business_name:
        google_data = await scrape_google_reviews(business_name, address)
        scraped["google_rating"] = google_data.get("google_rating")
        scraped["google_review_count"] = google_data.get("google_review_count")
        scraped["google_reviews"] = google_data.get("google_reviews", [])
        scraped["google_place_id"] = google_data.get("google_place_id")

    # Update record with scraped data
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        update_data = {
            "scrape_status": "completed",
            "last_scraped_at": now,
            "source_url": req.url,
            "business_name": scraped.get("business_name") or None,
            "phone": scraped.get("phone") or None,
            "email": scraped.get("email") or None,
            "address": scraped.get("address") or None,
            "about_text": scraped.get("about") or None,
            "hours": scraped.get("hours") or None,
            "logo_url": scraped.get("logo_url") or None,
            "social_links": scraped.get("social_links") or None,
        }
        if scraped.get("google_rating") is not None:
            update_data["google_rating"] = scraped["google_rating"]
            update_data["google_review_count"] = scraped.get("google_review_count")
            update_data["google_reviews"] = scraped.get("google_reviews", [])
            update_data["google_place_id"] = scraped.get("google_place_id")

        await db.update(
            "merchant_websites",
            update_data,
            filters={"id": f"eq.{existing[0]['id']}"},
        )

    return {"ok": True, "data": scraped}


@router.post("/generate")
async def generate_website_copy(req: GenerateRequest):
    """
    Generate AI copy (headline, subheadline, about) from current website data.
    Reads merchant_websites row, calls local Qwen LLM, and updates the record.
    """
    from ...services.website_scraper import generate_copy

    db = get_db()

    rows = await db.select(
        "merchant_websites",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "No website config found for this merchant")

    site = rows[0]

    business_data = {
        "business_name": site.get("business_name", ""),
        "business_type": site.get("business_type", ""),
        "about": site.get("about_text", ""),
        "address": site.get("address", ""),
    }

    copy = await generate_copy(business_data)

    # Update record with generated copy
    await db.update(
        "merchant_websites",
        {
            "hero_headline": copy.get("headline"),
            "hero_subheadline": copy.get("subheadline"),
            "about_text": copy.get("about"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        filters={"id": f"eq.{site['id']}"},
    )

    logger.info(f"Generated copy for merchant {req.merchant_id}")
    return {"ok": True, "copy": copy}


@router.post("/publish")
async def publish_website(req: PublishRequest):
    """
    Publish a merchant website. Validates that required fields are present.
    Sets published=true and published_at=now.
    """
    db = get_db()

    rows = await db.select(
        "merchant_websites",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "No website config found for this merchant")

    site = rows[0]

    # Validate required fields
    missing = []
    if not site.get("business_name"):
        missing.append("business_name")
    if not site.get("template_id"):
        missing.append("template_id")
    if not site.get("hero_headline"):
        missing.append("hero_headline")

    if missing:
        raise HTTPException(
            400,
            f"Cannot publish: missing required fields: {', '.join(missing)}",
        )

    now = datetime.now(timezone.utc).isoformat()
    slug = site.get("slug")
    if not slug:
        from ...services.website_scraper import generate_slug
        slug = generate_slug(site["business_name"])

    await db.update(
        "merchant_websites",
        {
            "published": True,
            "published_at": now,
            "slug": slug,
            "updated_at": now,
        },
        filters={"id": f"eq.{site['id']}"},
    )

    url = f"https://meridian.tips/sites/{slug}"

    logger.info(f"Published website for merchant {req.merchant_id}: {slug}")
    return {"ok": True, "slug": slug, "url": url}


@router.post("/unpublish")
async def unpublish_website(req: UnpublishRequest):
    """Unpublish a merchant website. Sets published=false."""
    db = get_db()

    rows = await db.select(
        "merchant_websites",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "No website config found for this merchant")

    await db.update(
        "merchant_websites",
        {
            "published": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        filters={"id": f"eq.{rows[0]['id']}"},
    )

    logger.info(f"Unpublished website for merchant {req.merchant_id}")
    return {"ok": True, "merchant_id": req.merchant_id}


@router.get("/public/{slug}")
async def get_public_website(slug: str):
    """
    Public endpoint — returns website data for the public renderer.
    No authentication required.

    If subscription_active is false, returns a limited payload.
    If active, returns full website data for rendering.
    """
    db = get_db()

    rows = await db.select(
        "merchant_websites",
        filters={
            "slug": f"eq.{slug}",
            "published": "eq.true",
        },
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "Website not found")

    site = rows[0]

    if not site.get("subscription_active"):
        return {
            "active": False,
            "business_name": site.get("business_name"),
        }

    # Return full public data (exclude sensitive/internal fields)
    return {
        "active": True,
        "business_name": site.get("business_name"),
        "business_type": site.get("business_type"),
        "tagline": site.get("tagline"),
        "description": site.get("description"),
        "template_id": site.get("template_id"),
        "template_config": site.get("template_config"),
        "logo_url": site.get("logo_url"),
        "hero_headline": site.get("hero_headline"),
        "hero_subheadline": site.get("hero_subheadline"),
        "about_text": site.get("about_text"),
        "services": site.get("services"),
        "hours": site.get("hours"),
        "phone": site.get("phone"),
        "email": site.get("email"),
        "address": site.get("address"),
        "google_rating": site.get("google_rating"),
        "google_review_count": site.get("google_review_count"),
        "google_reviews": site.get("google_reviews"),
        "social_links": site.get("social_links"),
        "slug": site.get("slug"),
        "ordering_enabled": site.get("ordering_enabled"),
    }


@router.post("/analytics")
async def record_analytics_event(req: AnalyticsEventRequest):
    """
    Public endpoint — record a website analytics event.
    Called by the public website renderer on page views, clicks, etc.
    """
    db = get_db()

    await db.insert("website_analytics", {
        "id": str(uuid4()),
        "merchant_id": req.merchant_id,
        "website_id": req.website_id,
        "event_type": req.event_type,
        "path": req.path,
        "referrer": req.referrer,
        "utm_source": req.utm_source,
        "utm_medium": req.utm_medium,
        "utm_campaign": req.utm_campaign,
        "device_type": req.device_type,
        "country": req.country,
        "city": req.city,
        "duration_seconds": req.duration_seconds,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"ok": True}


@router.get("/analytics/{merchant_id}")
async def get_analytics_summary(merchant_id: str):
    """
    Return an analytics summary for the merchant's website.
    Aggregates visitors today, this week, top referrers, device split, and UTM data.
    """
    if not _UUID_RE.match(merchant_id):
        raise HTTPException(400, "Invalid merchant_id format")
    db = get_db()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0,
    ).isoformat()

    # Visitors today (page_view events)
    today_events = await db.select(
        "website_analytics",
        filters={
            "merchant_id": f"eq.{merchant_id}",
            "event_type": "eq.page_view",
            "recorded_at": f"gte.{today_start}",
        },
    )

    # Visitors this week
    week_events = await db.select(
        "website_analytics",
        filters={
            "merchant_id": f"eq.{merchant_id}",
            "event_type": "eq.page_view",
            "recorded_at": f"gte.{week_start}",
        },
    )

    # All recent events for aggregation (last 30 days)
    month_start = (now - timedelta(days=30)).isoformat()
    all_events = await db.select(
        "website_analytics",
        filters={
            "merchant_id": f"eq.{merchant_id}",
            "recorded_at": f"gte.{month_start}",
        },
        order="recorded_at.desc",
        limit=5000,
    )

    # Top referrers
    referrer_counts: dict[str, int] = {}
    for e in all_events:
        ref = e.get("referrer")
        if ref:
            referrer_counts[ref] = referrer_counts.get(ref, 0) + 1
    top_referrers = sorted(referrer_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Device split
    device_counts: dict[str, int] = {}
    for e in all_events:
        dt = e.get("device_type", "unknown")
        device_counts[dt] = device_counts.get(dt, 0) + 1

    # UTM breakdown
    utm_sources: dict[str, int] = {}
    utm_mediums: dict[str, int] = {}
    utm_campaigns: dict[str, int] = {}
    for e in all_events:
        src = e.get("utm_source")
        med = e.get("utm_medium")
        camp = e.get("utm_campaign")
        if src:
            utm_sources[src] = utm_sources.get(src, 0) + 1
        if med:
            utm_mediums[med] = utm_mediums.get(med, 0) + 1
        if camp:
            utm_campaigns[camp] = utm_campaigns.get(camp, 0) + 1

    return {
        "merchant_id": merchant_id,
        "visitors_today": len(today_events),
        "visitors_this_week": len(week_events),
        "total_events_30d": len(all_events),
        "top_referrers": [{"referrer": r, "count": c} for r, c in top_referrers],
        "device_split": device_counts,
        "utm_sources": utm_sources,
        "utm_mediums": utm_mediums,
        "utm_campaigns": utm_campaigns,
    }


@router.post("/order")
async def create_website_order(req: CreateOrderRequest):
    """
    Public endpoint — create an order from a merchant website.
    Calculates subtotal from items, applies 2.99% platform fee, and stores the order.
    """
    db = get_db()

    # Look up the website to get merchant_id and fee config
    rows = await db.select(
        "merchant_websites",
        filters={"id": f"eq.{req.website_id}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "Website not found")

    site = rows[0]
    merchant_id = site["merchant_id"]

    if not site.get("ordering_enabled"):
        raise HTTPException(400, "Ordering is not enabled for this website")

    # Calculate subtotal from items
    subtotal = 0.0
    for item in req.items:
        price = float(item.get("price", 0))
        qty = int(item.get("quantity", 1))
        subtotal += price * qty

    # Round to 2 decimal places
    subtotal = round(subtotal, 2)

    # Apply platform fee (stored as decimal ratio, e.g. 0.0299 = 2.99%)
    fee_rate = site.get("ordering_fee_pct") or 0.0299
    fee_amount = round(subtotal * float(fee_rate), 2)
    total = round(subtotal + fee_amount, 2)

    order_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    currency = "CAD" if site.get("portal_context") == "canada" else "USD"

    await db.insert("website_orders", {
        "id": order_id,
        "merchant_id": merchant_id,
        "website_id": req.website_id,
        "customer_name": req.customer_name,
        "customer_phone": req.customer_phone,
        "customer_email": req.customer_email,
        "order_type": req.order_type,
        "items": req.items,
        "subtotal": subtotal,
        "fee_amount": fee_amount,
        "total": total,
        "currency": currency,
        "status": "pending",
        "created_at": now,
    })

    logger.info(f"Created order {order_id} for merchant {merchant_id}: ${total}")
    return {
        "ok": True,
        "order_id": order_id,
        "subtotal": subtotal,
        "fee_amount": fee_amount,
        "total": total,
        "currency": currency,
        "status": "pending",
    }


@router.get("/orders/{merchant_id}")
async def get_merchant_orders(
    merchant_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return recent orders for this merchant, newest first."""
    if not _UUID_RE.match(merchant_id):
        raise HTTPException(400, "Invalid merchant_id format")
    db = get_db()

    orders = await db.select(
        "website_orders",
        filters={"merchant_id": f"eq.{merchant_id}"},
        order="created_at.desc",
        limit=limit,
        offset=offset,
    )

    return {"merchant_id": merchant_id, "orders": orders, "count": len(orders)}


@router.delete("/{merchant_id}")
async def soft_delete_website(merchant_id: str):
    """
    Soft-delete a merchant website.
    Sets published=false and subdomain_active=false.
    Does not remove the record.
    """
    if not _UUID_RE.match(merchant_id):
        raise HTTPException(400, "Invalid merchant_id format")
    db = get_db()

    rows = await db.select(
        "merchant_websites",
        filters={"merchant_id": f"eq.{merchant_id}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "No website found for this merchant")

    await db.update(
        "merchant_websites",
        {
            "published": False,
            "subdomain_active": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        filters={"id": f"eq.{rows[0]['id']}"},
    )

    logger.info(f"Soft-deleted website for merchant {merchant_id}")
    return {"ok": True, "merchant_id": merchant_id}
