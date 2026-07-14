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
from datetime import datetime, timedelta, timezone

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
    """Resolve a short pay-link code to its hosted checkout URL and redirect.

    Stripe sessions are created up front, so the row already carries the URL.
    Clover Hosted Checkout sessions EXPIRE 15 MINUTES after creation, so
    provider='clover' rows are created LAZILY here on tap (and re-created when
    the stored session has expired) — see _clover_redirect below.
    """
    # codes are 8 hex chars; reject anything else fast (no DB hit for junk/scans)
    if not (4 <= len(code) <= 32 and code.isalnum()):
        raise HTTPException(404, "Unknown payment link")

    db = get_db()
    rows = await db.select(
        "checkout_sessions",
        columns="id,merchant_id,provider,provider_ref,checkout_url,status,payload,expires_at",
        filters={"short_code": f"eq.{code}"},
        limit=1,
    )
    if not rows:
        raise HTTPException(404, "Payment link not found or expired")
    row = rows[0]

    # Don't bounce the customer to a dead checkout page for a finished/voided
    # session — show a branded status page instead. Stripe checkout_session
    # statuses: "open" (payable), "complete" (paid), "expired". (For Clover,
    # 'expired'/'canceled' here means the ROW was voided; a merely-expired HCO
    # session keeps status='created' and is transparently re-created below.)
    status = (row.get("status") or "").lower()
    if status == "complete" or status == "paid":
        body = ("<h1>Already paid</h1><p>This order has already been paid — "
                "no further action needed. Thanks!</p>")
        return HTMLResponse(_page("Already paid", "✓", body), status_code=200)
    if status in ("expired", "canceled", "cancelled"):
        body = ("<h1>This payment link has expired</h1><p>Please ask the "
                "restaurant for a fresh link to complete your order.</p>")
        return HTMLResponse(_page("Link expired", "⌛", body, accent="#9A6700"), status_code=410)

    if (row.get("provider") or "").lower() == "clover":
        return await _clover_redirect(db, row)

    if not row.get("checkout_url"):
        raise HTTPException(404, "Payment link not found or expired")
    # 303 so the browser issues a clean GET to Stripe's hosted page.
    return RedirectResponse(url=row["checkout_url"], status_code=303)


# ── Clover Hosted Checkout: lazy session creation ──────────────────────────

def _hco_session_live(row: dict) -> bool:
    """True when the stored HCO session can still be redirected to: it exists
    and its expiry is safely in the future (30s margin so we never send a
    customer to a page that dies mid-card-entry)."""
    if not (row.get("provider_ref") and row.get("checkout_url")):
        return False
    from ...services.clover_hco import parse_expiration

    expires = parse_expiration(row.get("expires_at"))
    if expires is None:
        return False  # unknown expiry on a 15-min-TTL session → re-create
    return expires > datetime.now(timezone.utc) + timedelta(seconds=30)


async def _resolve_clover_credentials(db, merchant_id: str, payload: dict) -> tuple[str, str]:
    """(access_token, clover_merchant_id) for HCO creation, resolved at TAP
    time — the token is never stored in the checkout_sessions row. Mirrors the
    order-dispatch resolution (website_order_dispatch._resolve_connection):
    newest connected Clover pos_connections row, token decrypted; manual creds
    on phone_agent_config as fallback. merchant_id IS org_id in this system."""
    mid_hint = ((payload or {}).get("clover_merchant_id") or "").strip()
    if merchant_id:
        try:
            conns = await db.select(
                "pos_connections",
                filters={"org_id": f"eq.{merchant_id}", "provider": "eq.clover",
                         "status": "eq.connected"},
                order="updated_at.desc",
                limit=1,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("clover pay: pos_connections lookup failed: %s", e)
            conns = []
        if conns:
            from .phone_dashboard import _decrypt_connection_token

            token = (_decrypt_connection_token(conns[0]) or "").strip()
            mid = mid_hint or (conns[0].get("external_merchant_id") or "").strip()
            if token and mid:
                return token, mid
        try:
            cfg_rows = await db.select(
                "phone_agent_config",
                columns="pos_system,pos_access_token,pos_location_id",
                filters={"merchant_id": f"eq.{merchant_id}"},
                limit=1,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("clover pay: phone_agent_config lookup failed: %s", e)
            cfg_rows = []
        if cfg_rows and (cfg_rows[0].get("pos_system") or "") == "clover":
            token = (cfg_rows[0].get("pos_access_token") or "").strip()
            mid = mid_hint or (cfg_rows[0].get("pos_location_id") or "").strip()
            if token and mid:
                return token, mid
    return "", ""


async def _clover_redirect(db, row: dict):
    """Redirect to a live Clover Hosted Checkout session, creating (or
    re-creating, after the 15-min expiry) the session on demand."""
    from ...services.clover_hco import (
        HCO_SESSION_LIFETIME,
        create_hco_session,
        parse_expiration,
    )

    if _hco_session_live(row):
        return RedirectResponse(url=row["checkout_url"], status_code=303)

    payload = row.get("payload") or {}
    try:
        token, clover_mid = await _resolve_clover_credentials(
            db, row.get("merchant_id") or "", payload)
        if not (token and clover_mid):
            raise RuntimeError("clover_credentials_unavailable")
        hco = await create_hco_session(token, clover_mid, payload.get("hco_request") or {})
        expires = parse_expiration(hco.get("expirationTime")) or (
            datetime.now(timezone.utc) + HCO_SESSION_LIFETIME)
        try:
            await db.update(
                "checkout_sessions",
                {"provider_ref": hco["checkoutSessionId"],
                 "checkout_url": hco["href"],
                 "expires_at": expires.isoformat()},
                filters={"id": f"eq.{row.get('id')}"},
            )
        except Exception as e:  # noqa: BLE001 — persisting is best-effort; the
            # customer still pays on this session. A webhook for it would miss
            # the provider_ref match, so log loudly for follow-up.
            logger.error("clover pay: could not persist HCO session %s for row %s: %s",
                         hco.get("checkoutSessionId"), row.get("id"), e)
        logger.info("Clover HCO session %s created on tap for merchant %s (row %s)",
                    hco.get("checkoutSessionId"), row.get("merchant_id"), row.get("id"))
        return RedirectResponse(url=hco["href"], status_code=303)
    except Exception as e:  # noqa: BLE001 — never 500 a paying customer
        logger.error("clover pay: HCO creation failed for row %s: %s", row.get("id"), e)
        # Meridian-hosted checkout only when one is EXPLICITLY configured — the
        # default pay.meridian.ai/checkout page does not exist (it stranded CAD
        # orders before), so a friendly retry page beats a dead redirect.
        hosted_base = (os.getenv("MERIDIAN_CHECKOUT_URL") or "").rstrip("/")
        if hosted_base and row.get("id"):
            return RedirectResponse(url=f"{hosted_base}/checkout/{row['id']}", status_code=303)
        body = ("<h1>We couldn't open the payment page</h1>"
                "<p>Please try the link again in a moment, or pay at pickup — "
                "your order is saved.</p>")
        return HTMLResponse(_page("Payment page unavailable", "!", body,
                                  accent="#9A6700"), status_code=503)


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
