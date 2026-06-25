"""
Branded short pay-link redirect.

  GET /p/{code}  ->  302 to the stored Stripe Checkout URL

The phone agent texts customers `<PUBLIC_PAY_BASE>/p/<code>` instead of Stripe's
~400-char URL. The short code maps to checkout_sessions.checkout_url (written
when the session is created). Keeps the SMS clean + branded, and every hit is a
recorded click on the order.
"""
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from ...db import get_db

logger = logging.getLogger("meridian.api.pay_redirect")

router = APIRouter(tags=["pay-redirect"])


@router.get("/p/{code}")
async def pay_redirect(code: str):
    """Resolve a short pay-link code to its Stripe checkout URL and redirect."""
    # codes are 8 hex chars; reject anything else fast (no DB hit for junk/scans)
    if not (4 <= len(code) <= 32 and code.isalnum()):
        raise HTTPException(404, "Unknown payment link")

    db = await get_db()
    rows = await db.select(
        "checkout_sessions",
        columns="checkout_url,status",
        filters={"short_code": f"eq.{code}"},
        limit=1,
    )
    if not rows or not rows[0].get("checkout_url"):
        raise HTTPException(404, "Payment link not found or expired")

    # 303 so the browser issues a clean GET to Stripe's hosted page.
    return RedirectResponse(url=rows[0]["checkout_url"], status_code=303)
