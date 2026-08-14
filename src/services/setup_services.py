"""
Setup Services — one mechanism for every adder product.

    the merchant PAYS → a work order is created → it is posted to the Foundry
    dev marketplace → devs bid with actual work → the OWNER picks.

Adding a sellable adder is adding an entry to CATALOG below. Everything else —
the work-order record, the payment gate, the marketplace posting, the console
row — comes for free.

WHY THIS EXISTS: before it, each adder had invented its own path. Website
Buildout fired a Foundry contest from the browser at close; the 30-second spot
fired one from the API at close; Custom CRM build fired nothing at all and was
a line on an invoice. A fourth adder would have invented a fourth path.

PAYMENT IS THE TRIGGER. A work order is recorded when the rep closes, and
posted when the money lands (Stripe checkout.session.completed). Developers
should not do spec work against a deal that never paid. `SETUP_SERVICE_POST_ON_CLOSE=1`
restores close-time posting while the change is being watched.

Nothing here decides that work is finished — the owner picking on Foundry does
that, and delivery is recorded back by ops.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import httpx

logger = logging.getLogger("meridian.services.setup_services")

FOUNDRY_BASE = os.getenv("FOUNDRY_BASE_URL", "https://foundry.meridian.tips/agency")

#: Post at close instead of at payment. Off by default — see the module
#: docstring. Kept because flipping a live product's timing deserves a switch.
POST_ON_CLOSE = os.getenv("SETUP_SERVICE_POST_ON_CLOSE", "0") == "1"

#: Master switch for marketplace posting (kill switch, not a config knob).
MARKETPLACE_ENABLED = os.getenv("SETUP_SERVICE_MARKETPLACE", "1") != "0"


@dataclass(frozen=True)
class SetupService:
    """One sellable adder.

    `endpoint` is the Foundry route that opens its posting; `payload` turns the
    rep's brief into that route's body. A service whose work has no dedicated
    contest type uses the generic work-order posting — that is the default and
    it is a complete path, not a fallback.
    """
    kind: str
    label: str
    endpoint: str
    payload: Callable[[dict, dict], dict]
    #: False for services the rep prices per deal (Custom CRM build) — those
    #: carry no catalog price and the order records what the rep quoted.
    fixed_price: bool = True


def _common(order: dict) -> dict:
    """Fields every Foundry posting takes, however specialised it is."""
    return {
        "company": order.get("business_name") or "",
        "contactName": order.get("contact_name") or order.get("business_name") or "",
        "email": order.get("contact_email") or "",
    }


def _website_payload(order: dict, brief: dict) -> dict:
    pages = brief.get("pages") or []
    if isinstance(pages, str):
        pages = [p.strip() for p in pages.split(",") if p.strip()]
    raw_url = (brief.get("currentUrl") or "").strip()
    return {
        **_common(order),
        "currentUrl": raw_url if raw_url.startswith("http") or not raw_url else f"https://{raw_url}",
        "goals": brief.get("goals") or "",
        "pages": pages[:12] or ["Home"],
        "brandNotes": brief.get("brandNotes") or "",
        "contentReady": brief.get("contentReady") or "none",
    }


def _ad_spot_payload(order: dict, brief: dict) -> dict:
    return {
        **_common(order),
        "goal": brief.get("goal") or "",
        "highlights": brief.get("highlights") or "",
        "brandNotes": brief.get("brandNotes") or "",
        "placement": brief.get("placement") or "instagram_reel",
        "audio": brief.get("audio") or "voiceover_music",
        "durationSeconds": int(brief.get("durationSeconds") or 30),
    }


def _work_order_payload(order: dict, brief: dict) -> dict:
    """The generic posting: a title, a brief, a price, and what 'done' means.

    Used by every adder without a bespoke contest type. A developer bidding on
    this sees the same thing they would on any job — the actual scope and the
    actual money.
    """
    return {
        **_common(order),
        "serviceKind": order.get("service_kind") or "",
        "title": order.get("service_label") or "Setup service",
        "brief": brief.get("scope") or brief.get("goals") or brief.get("goal") or "",
        "acceptance": brief.get("acceptance") or "",
        "priceCents": int(order.get("price_cents") or 0),
        "currency": order.get("currency") or "USD",
    }


CATALOG: dict[str, SetupService] = {
    "website": SetupService(
        kind="website",
        label="Website Buildout",
        endpoint="/api/sites/order",
        payload=_website_payload,
    ),
    "ad_spot": SetupService(
        kind="ad_spot",
        label="30-Second AI Advertisement",
        endpoint="/api/spots/order",
        payload=_ad_spot_payload,
    ),
    "crm": SetupService(
        kind="crm",
        label="Custom CRM build",
        endpoint="/api/work-orders/order",
        payload=_work_order_payload,
        # Scoped per deal — the rep enters the amount they quoted.
        fixed_price=False,
    ),
}

#: Anything sold that is not in CATALOG still gets a work order and still
#: reaches the marketplace through the generic posting. A new adder is never
#: silently un-postable just because nobody registered it yet.
GENERIC = SetupService(
    kind="generic",
    label="Setup service",
    endpoint="/api/work-orders/order",
    payload=_work_order_payload,
)


def service_for(kind: str) -> SetupService:
    return CATALOG.get(kind, GENERIC)


# ── Supabase plumbing ────────────────────────────────────────────────────────

def _supabase() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"}


async def _patch(order_id: str, patch: dict) -> None:
    url, key = _supabase()
    if not url or not key:
        return
    body = {**patch, "updated_at": datetime.now(timezone.utc).isoformat()}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(
                f"{url}/rest/v1/setup_service_orders?id=eq.{order_id}",
                headers=_headers(key),
                json=body,
            )
        if resp.status_code not in (200, 204):
            logger.error("work order %s patch failed: %s %s", order_id, resp.status_code, resp.text[:200])
    except Exception as exc:  # noqa: BLE001 — a status write must never abort the flow
        logger.error("work order %s patch errored: %s", order_id, exc)


# ── The three things that happen to a work order ─────────────────────────────

async def record_work_order(
    *,
    service_kind: str,
    market: str,
    business_name: str,
    price_cents: int,
    brief: dict[str, Any],
    org_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    rep_id: Optional[str] = None,
    rep_name: Optional[str] = None,
    business_type: Optional[str] = None,
    contact_name: Optional[str] = None,
    contact_email: Optional[str] = None,
    service_label: Optional[str] = None,
) -> Optional[dict]:
    """Record a sold adder at close. Returns the row, or None if it could not
    be written (the caller decides how loudly to fail — a sold service that was
    never recorded is a real problem, so callers should surface it).

    Posting happens later, when the money lands.
    """
    url, key = _supabase()
    if not url or not key:
        logger.error("Supabase not configured — cannot record a sold setup service")
        return None

    service = service_for(service_kind)
    payload = {
        "org_id": org_id or None,
        "market": market,
        "lead_id": lead_id or None,
        "rep_id": rep_id or None,
        "rep_name": rep_name or None,
        "business_name": business_name,
        "business_type": business_type or None,
        "contact_name": contact_name or None,
        "contact_email": contact_email or None,
        "service_kind": service_kind,
        "service_label": service_label or service.label,
        "price_cents": max(int(price_cents), 0),
        "currency": "CAD" if market == "ca" else "USD",
        "brief": brief or {},
        "payment_status": "awaiting_payment",
        "status": "awaiting_payment",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{url}/rest/v1/setup_service_orders",
                headers={**_headers(key), "Prefer": "return=representation"},
                json=payload,
            )
    except Exception:  # noqa: BLE001 — logger.exception carries the traceback
        logger.exception("work order insert errored for %s", business_name)
        return None

    # 409 = the live-order unique index fired; the same service is already
    # open for this org, which is a double-submit, not a second purchase.
    if resp.status_code == 409:
        logger.info("work order already live: %s / %s", business_name, service_kind)
        return None
    if resp.status_code not in (200, 201) or not resp.json():
        logger.error("work order insert failed: %s %s", resp.status_code, resp.text[:300])
        return None

    row = resp.json()[0]
    logger.info("work order %s recorded: %s for %s", row["id"], service_kind, business_name)

    if POST_ON_CLOSE:
        await post_to_marketplace(row)
    return row


async def post_to_marketplace(order: dict) -> Optional[str]:
    """Put a paid work order on the Foundry board. Returns the job id.

    Best-effort by design: the merchant has paid and their service is owed
    either way, so a Foundry outage records a reason and leaves the order
    visible as `failed` for a human — it never raises into a payment webhook.
    """
    if not MARKETPLACE_ENABLED:
        return None

    order_id = order["id"]
    service = service_for(order.get("service_kind", ""))
    brief = order.get("brief") or {}
    if isinstance(brief, str):
        import json
        try:
            brief = json.loads(brief)
        except Exception:  # noqa: BLE001
            brief = {}

    await _patch(order_id, {"status": "posting"})

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{FOUNDRY_BASE}{service.endpoint}",
                json=service.payload(order, brief),
            )
        data = resp.json() if resp.content else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("work order %s not posted: %s", order_id, exc)
        await _patch(order_id, {"status": "failed", "status_detail": f"not posted: {exc}"[:300]})
        return None

    job_id = data.get("jobId")
    # 409 = a posting of this kind is already live for the business (a re-close).
    if resp.status_code in (200, 201, 409) and job_id:
        await _patch(order_id, {
            "status": "posted",
            "status_detail": "live on the Foundry board"
                             if resp.status_code != 409 else "reused the live posting",
            "foundry_job_id": job_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("work order %s posted as Foundry job %s", order_id, job_id)
        return job_id

    detail = data.get("error") or f"HTTP {resp.status_code}"
    logger.warning("work order %s rejected by Foundry: %s", order_id, detail)
    await _patch(order_id, {"status": "failed", "status_detail": f"not posted: {detail}"[:300]})
    return None


async def dispatch_paid_orders(
    *, org_id: Optional[str] = None, session_id: Optional[str] = None
) -> int:
    """The money landed → post everything this org bought.

    Called from the Stripe webhook. Idempotent: only orders still
    `awaiting_payment` are touched, so a webhook retry re-posts nothing. Never
    raises — a marketplace hiccup must not fail a verified payment event.
    """
    if not org_id:
        return 0
    url, key = _supabase()
    if not url or not key:
        return 0

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{url}/rest/v1/setup_service_orders"
                f"?org_id=eq.{org_id}&payment_status=eq.awaiting_payment&select=*",
                headers=_headers(key),
            )
        orders = resp.json() if resp.status_code == 200 else []
    except Exception as exc:  # noqa: BLE001
        logger.error("could not load work orders for org %s: %s", org_id, exc)
        return 0

    posted = 0
    for order in orders:
        await _patch(order["id"], {
            "payment_status": "paid",
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "stripe_session_id": session_id,
        })
        if await post_to_marketplace(order):
            posted += 1

    if orders:
        logger.info("org %s paid — %d/%d work orders posted", org_id, posted, len(orders))
    return posted
