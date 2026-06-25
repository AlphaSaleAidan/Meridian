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
import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

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
