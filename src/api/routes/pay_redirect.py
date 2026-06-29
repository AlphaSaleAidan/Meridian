"""
Branded short pay-link redirect + post-checkout pages.

  GET /p/{code}      ->  303 to the stored Stripe Checkout URL
  GET /pay/success   ->  branded "payment received" page (CAD amount)
  GET /pay/cancel    ->  branded "checkout cancelled" page

The phone agent texts customers `<PUBLIC_PAY_BASE>/p/<code>` instead of Stripe's
~400-char URL. The short code maps to checkout_sessions.checkout_url (written
when the session is created). Stripe's hosted Checkout handles card + Apple Pay
+ Google Pay + CAD natively; these pages are where it returns afterwards. They
live on the backend (api.meridian.tips) so they never fall through to the
frontend SPA home page (the bug the old meridian.tips/pay/success default hit).
"""
import io
import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ...db import get_db

logger = logging.getLogger("meridian.api.pay_redirect")

router = APIRouter(tags=["pay-redirect"])


def _page(title: str, heading: str, body: str, accent: str = "#0B6E4F") -> str:
    """One branded shell for the post-checkout pages — no template engine."""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · Meridian</title>
<style>
  :root{{color-scheme:light}}
  body{{margin:0;font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    background:#f6f7f9;color:#111;display:grid;min-height:100vh;place-items:center}}
  .card{{background:#fff;max-width:420px;width:calc(100% - 32px);padding:40px 28px;
    border-radius:16px;box-shadow:0 6px 24px rgba(0,0,0,.08);text-align:center}}
  .badge{{width:56px;height:56px;border-radius:50%;display:grid;place-items:center;
    margin:0 auto 18px;background:{accent}1a;color:{accent};font-size:28px}}
  h1{{font-size:22px;margin:0 0 8px}} p{{margin:6px 0;color:#444}}
  .amt{{font-size:32px;font-weight:700;color:{accent};margin:14px 0}}
  .brand{{margin-top:24px;font-size:13px;color:#999;letter-spacing:.04em}}
</style></head><body><div class="card">
  <div class="badge">{heading}</div>{body}
  <div class="brand">MERIDIAN</div>
</div></body></html>"""


@router.get("/p/{code}")
async def pay_redirect(code: str):
    """Resolve a short pay-link code to its Stripe checkout URL and redirect."""
    # codes are 8 hex chars; reject anything else fast (no DB hit for junk/scans)
    if not (4 <= len(code) <= 32 and code.isalnum()):
        raise HTTPException(404, "Unknown payment link")

    db = get_db()
    rows = await db.select(
        "checkout_sessions",
        columns="checkout_url,status",
        filters={"short_code": f"eq.{code}"},
        limit=1,
    )
    if not rows or not rows[0].get("checkout_url"):
        raise HTTPException(404, "Payment link not found or expired")

    # Don't bounce the customer to a dead Stripe page for a finished/expired
    # session — show a branded status page instead. Stripe checkout_session
    # statuses: "open" (payable), "complete" (paid), "expired".
    status = (rows[0].get("status") or "").lower()
    if status == "complete" or status == "paid":
        body = ("<h1>Already paid</h1><p>This order has already been paid — "
                "no further action needed. Thanks!</p>")
        return HTMLResponse(_page("Already paid", "✓", body), status_code=200)
    if status in ("expired", "canceled", "cancelled"):
        body = ("<h1>This payment link has expired</h1><p>Please ask the "
                "restaurant for a fresh link to complete your order.</p>")
        return HTMLResponse(_page("Link expired", "⌛", body, accent="#9A6700"), status_code=410)

    # 303 so the browser issues a clean GET to Stripe's hosted page.
    return RedirectResponse(url=rows[0]["checkout_url"], status_code=303)


@router.get("/pay/success", response_class=HTMLResponse)
async def pay_success(session_id: str = ""):
    """Branded confirmation after Stripe checkout. Reads the session to show the
    real amount in its currency; falls back to a generic thank-you if the lookup
    fails (never leave a paying customer on an error)."""
    amount_html = ""
    if session_id.startswith("cs_") and os.getenv("STRIPE_SECRET_KEY"):
        try:
            import stripe
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
            s = stripe.checkout.Session.retrieve(session_id)
            cur = (s["currency"] or "cad").upper()
            sym = "CA$" if cur == "CAD" else f"{cur} "
            amount_html = f'<div class="amt">{sym}{(s["amount_total"] or 0) / 100:,.2f}</div>'
        except Exception as e:  # noqa: BLE001 — display is best-effort
            logger.warning("success page session lookup failed: %s", e)
    body = (f"<h1>Payment received</h1>{amount_html}"
            "<p>Your order is confirmed and the restaurant has been notified.</p>"
            "<p>A receipt has been sent to your phone.</p>")
    return _page("Payment received", "✓", body)


@router.get("/pay/cancel", response_class=HTMLResponse)
async def pay_cancel():
    """Branded page when the customer backs out of Stripe checkout."""
    body = ("<h1>Checkout cancelled</h1>"
            "<p>No charge was made. Call the restaurant back any time to finish "
            "your order.</p>")
    return _page("Checkout cancelled", "↩", body, accent="#9A6700")


# ── Subscription short-links ───────────────────────────────────────────────
#
# These endpoints are PUBLIC (no auth) — the merchant scans a QR or taps a link.
# GET /subscribe/{token}      → creates a fresh Stripe subscription Checkout Session, 303 redirect
# GET /subscribe/{token}/qr.png → renders the subscribe URL as a PNG QR code
#
# A fresh session is created on every scan so the link/QR never expires.
# The flow is SEPARATE from the per-order $1.50 Connect fee:
#   no application_fee_amount, no transfer_data, direct charge to Meridian's account.

_PUBLIC_PAY_BASE = os.getenv("PUBLIC_PAY_BASE", "https://meridian.tips")


async def _create_sub_session(row: dict):
    """Create a Stripe subscription Checkout Session from a subscribe_links row.

    Returns the Stripe session object.  Raises HTTPException on misconfiguration.
    """
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    try:
        import stripe as _stripe
        _stripe.api_key = stripe_key
    except ImportError:
        raise HTTPException(status_code=501, detail="stripe package not installed")

    monthly_cents: int = row["monthly_amount_cents"]
    currency: str = (row.get("currency") or "cad").lower()
    business_name: str = row.get("business_name") or "Meridian Subscription"
    setup_fee_cents: int = row.get("setup_fee_cents") or 0
    first_month_free: bool = bool(row.get("first_month_free"))
    org_id: str = row.get("org_id") or ""
    lead_id: str = row.get("lead_id") or ""

    line_items = [
        {
            "price_data": {
                "currency": currency,
                "product_data": {
                    "name": f"Meridian Subscription — {business_name}",
                    "description": "Monthly analytics subscription",
                },
                "unit_amount": monthly_cents,
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }
    ]

    if setup_fee_cents > 0:
        line_items.append({
            "price_data": {
                "currency": currency,
                "product_data": {
                    "name": "Setup Fee",
                    "description": "One-time account setup and onboarding",
                },
                "unit_amount": setup_fee_cents,
            },
            "quantity": 1,
        })

    subscription_data: dict = {
        "metadata": {
            "kind": "subscription",
            "org_id": org_id,
            "lead_id": lead_id,
            "business_name": business_name,
        },
    }
    if first_month_free:
        subscription_data["trial_period_days"] = 30

    session = _stripe.checkout.Session.create(
        mode="subscription",
        line_items=line_items,
        subscription_data=subscription_data,
        success_url=f"{_PUBLIC_PAY_BASE}/pay/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{_PUBLIC_PAY_BASE}/pay/cancel",
        metadata={
            "kind": "subscription",
            "org_id": org_id,
            "lead_id": lead_id,
            "business_name": business_name,
        },
        allow_promotion_codes=True,
        billing_address_collection="required",
    )
    return session


@router.get("/subscribe/{token}")
async def subscribe_redirect(token: str):
    """Resolve a subscribe token → create a fresh Stripe subscription session → 303."""
    # Validate token shape: token_urlsafe(16) produces ~22 url-safe base64 chars
    if not (8 <= len(token) <= 64):
        raise HTTPException(404, "Unknown subscription link")

    db = get_db()
    rows = await db.select(
        "subscribe_links",
        columns="id,token,org_id,lead_id,monthly_amount_cents,currency,business_name,"
                "setup_fee_cents,first_month_free,status",
        filters={"token": f"eq.{token}"},
        limit=1,
    )
    if not rows:
        body = ("<h1>Subscription link not found</h1>"
                "<p>This link may have been revoked. Please contact your Meridian rep "
                "for a new link.</p>")
        return HTMLResponse(_page("Not found", "✗", body, accent="#9A6700"), status_code=404)

    row = rows[0]
    if (row.get("status") or "").lower() != "active":
        body = ("<h1>This subscription link is no longer active</h1>"
                "<p>Please contact your Meridian rep for an updated link.</p>")
        return HTMLResponse(_page("Link inactive", "⌛", body, accent="#9A6700"), status_code=410)

    try:
        session = await _create_sub_session(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create subscription checkout session for token=%s", token)
        raise HTTPException(status_code=500, detail=str(e))

    # Persist the latest Stripe session ID so the webhook can correlate back
    try:
        await db.update(
            "subscribe_links",
            {"stripe_session_id": session.id},
            filters={"token": f"eq.{token}"},
        )
    except Exception as e:
        logger.warning("Could not persist stripe_session_id for token=%s: %s", token, e)

    logger.info("Subscribe redirect: token=%s session=%s", token, session.id)
    return RedirectResponse(url=session.url, status_code=303)


@router.get("/subscribe/{token}/qr.png")
async def subscribe_qr(token: str):
    """Return a PNG QR code encoding the subscribe URL for the given token.

    The QR encodes ``{PUBLIC_PAY_BASE}/subscribe/{token}`` so scanning it is
    identical to tapping the link.  The code is re-generated on every request
    (cheap, stateless) so no caching table is needed.
    """
    if not (8 <= len(token) <= 64):
        raise HTTPException(404, "Unknown subscription link")

    # Verify token exists and is active before burning a QR (avoids leaking tokens)
    db = get_db()
    rows = await db.select(
        "subscribe_links",
        columns="status",
        filters={"token": f"eq.{token}"},
        limit=1,
    )
    if not rows or (rows[0].get("status") or "").lower() != "active":
        raise HTTPException(404, "Subscription link not found or inactive")

    subscribe_url = f"{_PUBLIC_PAY_BASE}/subscribe/{token}"

    try:
        import qrcode
        from qrcode.image.pil import PilImage
        qr = qrcode.QRCode(
            version=None,          # auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(subscribe_url)
        qr.make(fit=True)
        img = qr.make_image(image_factory=PilImage)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="qrcode[pil] not installed. Run: pip install 'qrcode[pil]'"
        )
    except Exception as e:
        logger.exception("QR generation failed for token=%s", token)
        raise HTTPException(status_code=500, detail=str(e))

    return Response(content=png_bytes, media_type="image/png")
