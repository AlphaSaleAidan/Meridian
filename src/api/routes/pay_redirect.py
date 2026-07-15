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


@router.get("/pay/clover/return/{code}", response_class=HTMLResponse)
async def clover_return(code: str):
    """Success-return for Clover-NATIVE hosted checkout (pay-by-text on the
    merchant's own Clover processing).

    The redirect itself is NEVER trusted — anyone can load this URL. We verify
    server-side against the merchant's Clover payments API (amount match inside
    the session window) before marking the phone order paid, releasing the
    kitchen ticket, and booking Meridian's fee to the voice ledger. Until the
    payment is visible, the customer gets a self-refreshing 'confirming' page.
    """
    if not (4 <= len(code) <= 32 and code.isalnum()):
        raise HTTPException(404, "Unknown payment link")

    db = get_db()
    rows = await db.select(
        "checkout_sessions",
        columns="merchant_id,pos_order_id,provider,provider_ref,amount_cents,"
                "currency,status,caller_phone,created_at",
        filters={"short_code": f"eq.{code}", "provider": "eq.clover_hco"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "Payment link not found")
    sess = rows[0]

    cur = (sess.get("currency") or "cad").upper()
    sym = "CA$" if cur == "CAD" else f"{cur} "
    amt_html = f'<div class="amt">{sym}{(sess.get("amount_cents") or 0) / 100:,.2f}</div>'
    paid_body = (f"<h1>Payment received</h1>{amt_html}"
                 "<p>Your order is confirmed and the restaurant has been notified.</p>")

    if (sess.get("status") or "").lower() in ("paid", "complete"):
        return HTMLResponse(_page("Payment received", "✓", paid_body))

    payment = await _verify_clover_payment(sess)
    if not payment:
        body = ("<h1>Confirming your payment…</h1>"
                "<p>Hang tight — we're confirming with the register. This page "
                "refreshes automatically.</p>"
                "<script>setTimeout(function(){location.reload()},6000)</script>")
        return HTMLResponse(_page("Confirming payment", "⏳", body, accent="#9A6700"))

    merchant_id = sess.get("merchant_id", "")
    txn = str(payment.get("id") or "")

    # Release the held phone order (idempotent inside mark_order_paid).
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _pa = str(_Path(__file__).resolve().parents[3] / "services" / "phone_agent")
        if _pa not in _sys.path:
            _sys.path.insert(0, _pa)
        from pay_on_phone import mark_order_paid

        released = await mark_order_paid(
            merchant_id=merchant_id,
            caller_phone=sess.get("caller_phone", "") or "",
            pos_order_id=sess.get("pos_order_id", "") or "",
            method="clover",
            payment_txn_id=txn,
        )
        logger.info("Clover native payment verified → order released: %s", released)
    except Exception as e:  # noqa: BLE001 — the customer paid; never error the page
        logger.error("clover native mark_order_paid failed for %s: %s", merchant_id, e)

    # Book Meridian's fee. The money ran on the merchant's Clover, so nothing
    # was auto-deducted — the ledger is how this fee gets settled at billing.
    # Idempotent on (source, ref): a reload can't double-post.
    try:
        fee_cents = _clover_native_fee_cents(sess)
        if fee_cents > 0 and merchant_id:
            from ...services.voice_ledger import credit
            await credit(merchant_id, fee_cents, source="clover_native_fee",
                         ref=txn or code, note=sess.get("pos_order_id") or code)
    except Exception as e:  # noqa: BLE001 — ledger never blocks the customer page
        logger.error("clover native fee credit failed for %s: %s", merchant_id, e)

    try:
        await db.update("checkout_sessions", {"status": "paid"},
                        filters={"short_code": f"eq.{code}"})
    except Exception as e:  # noqa: BLE001
        logger.warning("could not mark checkout_session %s paid: %s", code, e)

    # Paid receipt text — same promise the Stripe rail makes.
    phone = (sess.get("caller_phone") or "").strip()
    if phone:
        try:
            from ...sms.client import send_sms
            await send_sms(phone, (
                f"Payment received ✓ Your order is confirmed and paid — "
                f"{sym}{(sess.get('amount_cents') or 0) / 100:,.2f}. "
                "We'll have it ready shortly."))
        except Exception as e:  # noqa: BLE001 — receipt never blocks the page
            logger.warning("clover native receipt SMS failed: %s", e)

    return HTMLResponse(_page("Payment received", "✓",
                              paid_body + "<p>A receipt has been sent to your phone.</p>"))


async def _verify_clover_payment(sess: dict) -> dict | None:
    """Find a SUCCESS payment on the merchant's Clover matching this session's
    amount, created after the session was. Returns the payment or None."""
    import sys as _sys
    from datetime import datetime, timezone
    from pathlib import Path as _Path

    _pa = str(_Path(__file__).resolve().parents[3] / "services" / "phone_agent")
    if _pa not in _sys.path:
        _sys.path.insert(0, _pa)
    from merchant_config import get_merchant_config

    cfg = await get_merchant_config(sess.get("merchant_id", ""))
    token = (getattr(cfg, "pos_access_token", "") or "").strip() if cfg else ""
    clover_mid = (getattr(cfg, "pos_location_id", "") or "").strip() if cfg else ""
    if not (token and clover_mid):
        return None

    base = ("https://apisandbox.dev.clover.com"
            if os.getenv("CLOVER_ENVIRONMENT", "").strip().lower() == "sandbox"
            else "https://api.clover.com")

    created_ms = 0
    try:
        raw = (sess.get("created_at") or "").replace("Z", "+00:00")
        created_ms = int(datetime.fromisoformat(raw).timestamp() * 1000)
    except Exception:  # noqa: BLE001 — fall back to a 2h window
        created_ms = int((datetime.now(timezone.utc).timestamp() - 7200) * 1000)

    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{base}/v3/merchants/{clover_mid}/payments",
                params={"limit": "50", "filter": f"createdTime>={created_ms}"},
                headers={"Authorization": f"Bearer {token}"},
            )
    except Exception as e:  # noqa: BLE001 — treat as not-yet-verified
        logger.warning("clover payment verify request failed: %s", e)
        return None
    if res.status_code != 200:
        logger.warning("clover payment verify HTTP %s", res.status_code)
        return None

    want = int(sess.get("amount_cents") or -1)
    for p in (res.json() or {}).get("elements", []):
        if int(p.get("amount", -2)) == want and \
                (p.get("result") or "SUCCESS").upper() == "SUCCESS":
            return p
    return None


def _clover_native_fee_cents(sess: dict) -> int:
    """Meridian's fee for a Clover-native payment — mirrors the Stripe rail's
    application fee: split model = customer surcharge (already charged as a
    line item) + merchant-side %, else the flat MERIDIAN_SERVICE_FEE_CENTS."""
    import sys as _sys
    from pathlib import Path as _Path

    _pa = str(_Path(__file__).resolve().parents[3] / "services" / "phone_agent")
    if _pa not in _sys.path:
        _sys.path.insert(0, _pa)
    import payment_links as _pl

    amount = int(sess.get("amount_cents") or 0)
    if _pl.FEE_SPLIT_ENABLED and amount > 0:
        currency = (sess.get("currency") or "cad").lower()
        # plan tier isn't on the session row; standard-tier surcharge is the
        # floor — billing can true-up from the ledger note if needed.
        surcharge = _pl.customer_surcharge_cents("", currency)
        subtotal = max(amount - surcharge, 0)
        return _pl.split_application_fee_cents(subtotal, surcharge)
    return int(os.getenv("MERIDIAN_SERVICE_FEE_CENTS", "0") or 0)


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
#   (QR is generated client-side from this URL by the rep portal — no server-side QR endpoint)
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
