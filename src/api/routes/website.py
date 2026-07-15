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
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from ..auth import enforce_service_member, rate_limit_scrape, require_service_auth
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
    meta_title: str | None = None
    meta_description: str | None = None
    og_image_url: str | None = None
    custom_domain: str | None = None
    google_analytics_id: str | None = None


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
async def get_website_config(merchant_id: str = Query(...), principal=Depends(require_service_auth)):
    """
    Return the merchant's website configuration.
    If no record exists, returns {exists: false}.
    """
    await enforce_service_member(principal, merchant_id)
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
async def save_website_config(req: WebsiteConfigRequest, principal=Depends(require_service_auth)):
    """
    Create or update a merchant_websites record.
    Auto-generates a slug from business_name if not provided.
    """
    await enforce_service_member(principal, req.merchant_id)
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
async def scrape_merchant_website(req: ScrapeRequest, principal=Depends(require_service_auth)):
    """
    Scrape a business website for structured info.
    Updates scrape_status on the merchant_websites record.
    """
    await enforce_service_member(principal, req.merchant_id)
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
async def generate_website_copy(req: GenerateRequest, principal=Depends(require_service_auth)):
    """
    Generate AI copy (headline, subheadline, about) from current website data.
    Reads merchant_websites row, calls local Qwen LLM, and updates the record.
    """
    await enforce_service_member(principal, req.merchant_id)
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
async def publish_website(req: PublishRequest, principal=Depends(require_service_auth)):
    """
    Publish a merchant website. Validates that required fields are present.
    Sets published=true and published_at=now.
    """
    await enforce_service_member(principal, req.merchant_id)
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
async def unpublish_website(req: UnpublishRequest, principal=Depends(require_service_auth)):
    """Unpublish a merchant website. Sets published=false."""
    await enforce_service_member(principal, req.merchant_id)
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
        "id": site.get("id"),  # needed by the ordering cart to POST /order
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
        "meta_title": site.get("meta_title"),
        "meta_description": site.get("meta_description"),
        "og_image_url": site.get("og_image_url"),
        "custom_domain": site.get("custom_domain"),
        "google_analytics_id": site.get("google_analytics_id"),
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
async def get_analytics_summary(merchant_id: str, principal=Depends(require_service_auth)):
    """
    Return an analytics summary for the merchant's website.
    Aggregates visitors today, this week, top referrers, device split, and UTM data.
    """
    await enforce_service_member(principal, merchant_id)
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

    Fee model (matches services/phone_agent/payment_links.py):
      • fee split enabled → the CUSTOMER pays subtotal + Meridian's per-order
        fee (by the merchant's plan tier) + the fixed 30¢ (fee_amount); the
        MERCHANT-side 2.99% of the subtotal is recorded separately
        (merchant_fee_amount) and settled out of the payout, never added to
        the customer total.
      • legacy → 2.99% added on top of the customer total (fee_amount).
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

    currency = "CAD" if site.get("portal_context") == "canada" else "USD"

    # Platform fee rate (stored as decimal ratio, e.g. 0.0299 = 2.99%)
    fee_rate = site.get("ordering_fee_pct") or 0.0299

    # Fee helpers live in services/phone_agent — same sys.path trick phone.py uses.
    import sys
    from pathlib import Path as _Path
    _phone_agent_dir = str(_Path(__file__).resolve().parents[3] / "services" / "phone_agent")
    if _phone_agent_dir not in sys.path:
        sys.path.insert(0, _phone_agent_dir)
    import payment_links  # type: ignore[import]

    # Merchant payment/tier config drives the fee model AND the Stripe Connect
    # routing (destination charge to their account vs platform-direct).
    plan_tier = ""
    stripe_account_id = ""
    stripe_charges_enabled = False
    order_fee_cents = None
    try:
        cfg_rows = await db.select(
            "phone_agent_config",
            "plan_tier,stripe_account_id,stripe_charges_enabled,order_fee_cents",
            filters={"merchant_id": f"eq.{merchant_id}"}, limit=1,
        )
        if cfg_rows:
            plan_tier = (cfg_rows[0].get("plan_tier") or "")
            stripe_account_id = (cfg_rows[0].get("stripe_account_id") or "").strip()
            stripe_charges_enabled = bool(cfg_rows[0].get("stripe_charges_enabled"))
            if cfg_rows[0].get("order_fee_cents") is not None:
                order_fee_cents = int(cfg_rows[0]["order_fee_cents"])
    except Exception as e:  # noqa: BLE001 — unknown tier → default rate, platform charge
        logger.warning(f"payment config lookup failed for {merchant_id}: {e}")

    if payment_links.FEE_SPLIT_ENABLED:
        fee_amount = round(
            payment_links.customer_surcharge_cents(
                plan_tier, currency.lower(), override_cents=order_fee_cents) / 100, 2)
        merchant_fee_amount = round(subtotal * float(fee_rate), 2)
    else:
        fee_amount = round(subtotal * float(fee_rate), 2)
        merchant_fee_amount = 0.0
    total = round(subtotal + fee_amount, 2)

    order_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    order_row = {
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
        # Pay-first flow: every mobile order is paid through Stripe BEFORE the
        # kitchen sees it. The Connect webhook flips this to "paid" and only
        # then releases the POS/kitchen dispatch (as a PAID ticket).
        "status": "awaiting_payment",
        "created_at": now,
    }
    if payment_links.FEE_SPLIT_ENABLED:
        # Column ships in migration 036 — only referenced when the split is on,
        # so deploys with the flag off don't depend on the migration.
        order_row["merchant_fee_amount"] = merchant_fee_amount
    await db.insert("website_orders", order_row)

    # Stripe Checkout for the full customer total. Item lines charge the
    # subtotal; under the fee split _stripe_checkout adds the surcharge line
    # itself (same helper that produced fee_amount above), under legacy we add
    # the ordering fee as its own line — either way charge == `total`.
    checkout_items = [
        {
            "name": item.get("name", "Item"),
            "price": item.get("price", 0),
            "quantity": item.get("quantity", 1),
        }
        for item in req.items
    ]
    if not payment_links.FEE_SPLIT_ENABLED and fee_amount > 0:
        checkout_items.append({"name": "Online ordering fee", "price": fee_amount, "quantity": 1})

    site_base = os.getenv("PUBLIC_SITE_BASE", "https://meridian.tips").rstrip("/")
    site_url = f"{site_base}/sites/{site.get('slug', '')}"
    from types import SimpleNamespace
    merchant_cfg = SimpleNamespace(
        plan_tier=plan_tier,
        stripe_account_id=stripe_account_id,
        stripe_charges_enabled=stripe_charges_enabled,
        order_fee_cents=order_fee_cents,
    )
    try:
        checkout = await payment_links.create_website_checkout(
            {
                "merchant_id": merchant_id,
                "caller_phone": req.customer_phone or "",
                "currency": currency.lower(),
                "items": checkout_items,
                "total": subtotal if payment_links.FEE_SPLIT_ENABLED else total,
            },
            merchant_cfg,
            website_order_id=order_id,
            success_url=f"{site_url}?order=success&oid={order_id}",
            cancel_url=f"{site_url}?order=cancelled&oid={order_id}",
        )
    except Exception as e:  # noqa: BLE001 — fail closed: unpaid orders never reach the kitchen
        logger.error(f"Stripe checkout create failed for order {order_id}: {e}")
        try:
            await db.update("website_orders", {"status": "payment_unavailable"},
                            {"id": f"eq.{order_id}"})
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(
            503,
            "Online payment is temporarily unavailable — please call the restaurant to order.",
        )

    try:
        await db.update("website_orders", {"stripe_session_id": checkout.get("session_id", "")},
                        {"id": f"eq.{order_id}"})
    except Exception as e:  # noqa: BLE001 — pre-migration-040 schema; webhook metadata still links them
        logger.warning(f"could not record stripe_session_id on order {order_id}: {e}")

    logger.info(
        f"Created order {order_id} for merchant {merchant_id}: ${total} → awaiting Stripe payment"
    )
    return {
        "ok": True,
        "order_id": order_id,
        "subtotal": subtotal,
        "fee_amount": fee_amount,
        "merchant_fee_amount": merchant_fee_amount,
        "total": total,
        "currency": currency,
        "status": "awaiting_payment",
        "checkout_url": checkout.get("checkout_url") or checkout.get("url", ""),
        "pay_url": checkout.get("url", ""),
    }


@router.get("/order/{order_id}/status")
async def get_order_status(order_id: str):
    """Public, minimal order status — polled by the post-checkout success page
    so the customer can see their ticket reach the kitchen. Exposes nothing but
    coarse status strings for an unguessable UUID."""
    if not _UUID_RE.match(order_id):
        raise HTTPException(400, "Invalid order id")
    db = get_db()
    rows = await db.select(
        "website_orders", "id,status,pos_status",
        filters={"id": f"eq.{order_id}"}, limit=1,
    )
    if not rows:
        raise HTTPException(404, "Order not found")
    return {
        "order_id": order_id,
        "status": rows[0].get("status"),
        "pos_status": rows[0].get("pos_status"),
    }


@router.get("/orders/{merchant_id}")
async def get_merchant_orders(
    merchant_id: str,
    principal=Depends(require_service_auth),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return recent orders for this merchant, newest first."""
    await enforce_service_member(principal, merchant_id)
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
async def soft_delete_website(merchant_id: str, principal=Depends(require_service_auth)):
    """
    Soft-delete a merchant website.
    Sets published=false and subdomain_active=false.
    Does not remove the record.
    """
    await enforce_service_member(principal, merchant_id)
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
