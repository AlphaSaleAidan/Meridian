"""GET /b/{code} — resolve a texted booking link.

Mounted at the ROOT, not under /api, because this URL is typed into a phone
keyboard when a text is forwarded and read aloud when a text cannot be
delivered. Every character costs.

PUBLIC AND UNAUTHENTICATED BY CONSTRUCTION. The code arrives by SMS and is
tapped from a phone with no session, so there is nothing to authenticate
against. That is safe only because resolving a code grants exactly one thing:
a redirect to a URL the merchant already publishes. It must never be extended
into a key for anything else — no booking details, no caller name, no
merchant data in the response.
"""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.services.booking_links import get_link_service

logger = logging.getLogger("meridian.routes.booking_link")

router = APIRouter(tags=["bookings"])

_GONE = """<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Link not found</title>
<style>body{font:16px/1.5 system-ui,sans-serif;margin:0;display:grid;
place-items:center;min-height:100vh;background:#0B0B0F;color:#F5F5F7}
div{max-width:22rem;padding:2rem;text-align:center}p{color:#A1A1A8}</style>
<div><h1>That link has expired</h1>
<p>Give the restaurant a call and we'll send you a fresh one.</p></div>"""


@router.get("/b/{code}")
async def resolve_booking_link(code: str, request: Request):
    """302 to the merchant's booking page, counting the click on the way past.

    The redirect is issued even if the click cannot be recorded: a caller
    standing in the street waiting for a booking page is not the right person
    to pay for our analytics being unavailable.
    """
    clean = (code or "").strip()
    # Codes are fixed-length from a known alphabet; anything else is a scanner
    # and does not deserve a database round trip.
    if not clean or len(clean) > 16 or not clean.isalnum():
        return HTMLResponse(_GONE, status_code=404)

    try:
        row = await get_link_service().resolve(clean)
    except Exception as e:  # noqa: BLE001
        logger.warning("booking link lookup failed for %s: %s", clean, e)
        return HTMLResponse(_GONE, status_code=404)

    if not row or not row.get("target_url"):
        return HTMLResponse(_GONE, status_code=404)

    try:
        await get_link_service().record_click(row)
    except Exception:  # noqa: BLE001
        pass

    # 302, deliberately not 301: a permanent redirect would be cached by the
    # phone's browser and the second tap would never reach us, silently
    # capping every caller's click count at one.
    return RedirectResponse(row["target_url"], status_code=302)
