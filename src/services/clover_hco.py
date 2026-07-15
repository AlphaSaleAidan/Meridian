"""
Clover Hosted Checkout (HCO) — the real Clover payment-page API.

    POST {host}/invoicingcheckoutservice/v1/checkouts
    Headers: Authorization: Bearer <merchant OAuth access token>
             X-Clover-Merchant-Id: <clover merchant id>
    Body:    {"customer": {...}, "shoppingCart": {"lineItems": [...]}}
    Returns: {"href": <hosted page URL>, "checkoutSessionId": ..., "expirationTime": ...}

Sessions expire 15 minutes after creation, so callers create them lazily when
the customer taps the branded /p short link (pay_redirect.py), never at
SMS-send time. HCO ignores the merchant's Clover tax config and inventory —
tax must be computed INTO the line items by the caller.

Payment confirmation arrives on a dedicated HCO webhook (configured
per-merchant in the Clover dashboard: Settings → Ecommerce → Hosted Checkout;
the merchant pastes our URL and generates a signing secret). Signature is
HMAC-SHA256 delivered in the `Clover-Signature` header.
"""
import hashlib
import hmac
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger("meridian.services.clover_hco")

# Fallback assumption for the 15-minute HCO session lifetime, used when the
# create response's expirationTime is missing/unparseable. One minute of
# safety margin so we never text/redirect into a page about to die.
HCO_SESSION_LIFETIME = timedelta(minutes=14)


def hco_base_url() -> str:
    """HCO host, following clover_kitchen.py's CLOVER_ENVIRONMENT convention —
    the module live orders dispatch through today: PRODUCTION unless
    CLOVER_ENVIRONMENT=sandbox is set explicitly. (src/config.py defaults the
    other way; for the money path an unset env must mean the real host, never
    a silent sandbox.) CLOVER_HCO_BASE overrides for tests."""
    override = os.getenv("CLOVER_HCO_BASE", "")
    if override:
        return override.rstrip("/")
    if os.getenv("CLOVER_ENVIRONMENT", "").strip().lower() == "sandbox":
        return "https://apisandbox.dev.clover.com"
    region = os.getenv("CLOVER_REGION", "na").lower()
    return {
        "na": "https://api.clover.com",
        "eu": "https://api.eu.clover.com",
        "la": "https://api.la.clover.com",
    }.get(region, "https://api.clover.com")


async def create_hco_session(
    access_token: str, clover_merchant_id: str, body: dict[str, Any]
) -> dict[str, Any]:
    """Create a Hosted Checkout session. `body` is the ready-to-POST HCO
    request ({"customer": ..., "shoppingCart": ...}). Raises RuntimeError on
    any non-2xx so callers can fall back without parsing a broken response."""
    if not (access_token and clover_merchant_id):
        raise RuntimeError("clover_hco_missing_credentials")
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            f"{hco_base_url()}/invoicingcheckoutservice/v1/checkouts",
            json=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Clover-Merchant-Id": clover_merchant_id,
                "Content-Type": "application/json",
            },
        )
    if res.status_code not in (200, 201):
        logger.warning("Clover HCO create failed %s: %s", res.status_code, res.text[:300])
        raise RuntimeError(f"clover_hco_create_{res.status_code}")
    data = res.json()
    if not data.get("href") or not data.get("checkoutSessionId"):
        raise RuntimeError("clover_hco_create_malformed_response")
    return data


def parse_expiration(value: Any) -> datetime | None:
    """Parse HCO expirationTime into an aware UTC datetime.

    Clover's docs are thin on the exact wire format, so accept the shapes seen
    across their APIs: epoch milliseconds (int or numeric string) and ISO-8601
    (with or without a trailing Z). Returns None when unparseable — callers
    fall back to now + HCO_SESSION_LIFETIME.
    """
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            ms = float(value)
            # epoch seconds vs milliseconds: anything past year ~2100 in
            # seconds is clearly milliseconds.
            if ms > 4_102_444_800:
                ms /= 1000.0
            return datetime.fromtimestamp(ms, tz=timezone.utc)
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001 — unparseable → None (caller has a fallback)
        logger.warning("Unparseable HCO expirationTime: %r", value)
    return None


def _hex_hmac(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_hco_signature(secret: str, body: bytes, header: str) -> bool:
    """Verify a `Clover-Signature` header against the raw request body.

    Documented assumption (Clover's HCO webhook docs are thin — validate
    against a real sandbox merchant before pilot): the header is Stripe-style
    `t=<timestamp>,v1=<hex>` with the HMAC-SHA256 computed over
    `<timestamp>.<payload>`. Verified TOLERANTLY:
      • a bare `v1=<hex>` (or a bare hex digest) is also accepted, checked
        against HMAC(body) alone;
      • when `t=` is present, both `<t>.<body>` and bare `<body>` are tried;
      • NO timestamp-freshness window is enforced (we don't know Clover's
        retry cadence; replay of an APPROVED event is idempotent downstream).
    Always constant-time compares. Missing secret/header → False (fail closed).
    """
    if not secret or not header or not body:
        return False

    ts = ""
    candidates: list[str] = []
    for part in header.split(","):
        part = part.strip()
        if part.startswith("t="):
            ts = part[2:].strip()
        elif part.startswith("v1="):
            candidates.append(part[3:].strip().lower())
    if not candidates and re.fullmatch(r"[0-9a-fA-F]{64}", header.strip()):
        candidates.append(header.strip().lower())
    if not candidates:
        return False

    messages = [body]
    if ts:
        messages.insert(0, f"{ts}.".encode("utf-8") + body)

    for sig in candidates:
        for message in messages:
            if hmac.compare_digest(_hex_hmac(secret, message), sig):
                return True
    return False


# ── Settlement (shared by the /pay/clover/return page and the HCO webhook) ──

def _phone_agent_path() -> str:
    import sys
    from pathlib import Path

    pa = str(Path(__file__).resolve().parents[2] / "services" / "phone_agent")
    if pa not in sys.path:
        sys.path.insert(0, pa)
    return pa


def clover_fee_cents(sess: dict[str, Any]) -> int:
    """Meridian's fee for a Clover-native payment — mirrors the Stripe rail's
    application fee: split model = customer surcharge (already charged as a
    cart line item) + merchant-side % of the subtotal, else the flat
    MERIDIAN_SERVICE_FEE_CENTS. The merchant's plan tier and any
    rep-negotiated fee override travel in the session payload (written at
    order time) so billing gets the exact negotiated fee."""
    _phone_agent_path()
    import payment_links as _pl

    amount = int(sess.get("amount_cents") or 0)
    if _pl.FEE_SPLIT_ENABLED and amount > 0:
        currency = (sess.get("currency") or "cad").lower()
        payload = sess.get("payload") or {}
        plan_tier = (payload.get("plan_tier") or "").strip()
        override = payload.get("fee_override_cents")
        surcharge = _pl.customer_surcharge_cents(
            plan_tier, currency,
            override_cents=(int(override) if override is not None else None))
        subtotal = max(amount - surcharge, 0)
        return _pl.split_application_fee_cents(subtotal, surcharge)
    # Flat model: the rep-negotiated per-order fee still wins over the env
    # default — mirrors the Stripe rail (application_fee_cents(service_fee_
    # cents=override) / _merchant_service_fee_cents). Without this, live
    # flat-model Clover settlements booked the env fee and silently ignored
    # what the rep sold.
    override = (sess.get("payload") or {}).get("fee_override_cents")
    if override is not None:
        try:
            return max(int(override), 0)
        except (TypeError, ValueError):
            pass
    return int(os.getenv("MERIDIAN_SERVICE_FEE_CENTS", "0") or 0)


async def settle_clover_session(db, sess: dict[str, Any], payment_ref: str) -> None:
    """Everything that must happen once a Clover-native payment is TRUSTED
    (server-side verified at /pay/clover/return, or signature-verified on the
    per-merchant HCO webhook): release the held phone order, book Meridian's
    fee to the voice ledger, mark the checkout_sessions row paid, and text the
    receipt. Both confirmation paths may fire for the same payment — every
    step is guarded and idempotent (mark_order_paid internally; the ledger on
    (source, ref); the row/status update by value), so double-settling is a
    no-op. Never raises: the customer has already paid."""
    merchant_id = (sess.get("merchant_id") or "").strip()
    ref = (payment_ref or "").strip() or (sess.get("short_code") or "")

    try:
        _phone_agent_path()
        from pay_on_phone import mark_order_paid

        released = await mark_order_paid(
            merchant_id=merchant_id,
            caller_phone=sess.get("caller_phone", "") or "",
            pos_order_id=sess.get("pos_order_id", "") or "",
            method="clover",
            payment_txn_id=ref,
        )
        logger.info("Clover native payment settled → order released: %s", released)
    except Exception as e:  # noqa: BLE001 — the customer paid; keep settling
        logger.error("clover settle: mark_order_paid failed for %s: %s", merchant_id, e)

    # The money ran on the merchant's Clover, so nothing was auto-deducted —
    # the ledger is how Meridian's fee gets collected at billing.
    try:
        fee = clover_fee_cents(sess)
        if fee > 0 and merchant_id:
            from .voice_ledger import credit

            await credit(merchant_id, fee, source="clover_native_fee",
                         ref=ref, note=sess.get("pos_order_id") or sess.get("short_code"))
    except Exception as e:  # noqa: BLE001 — ledger never blocks settlement
        logger.error("clover settle: fee credit failed for %s: %s", merchant_id, e)

    try:
        await db.update("checkout_sessions", {"status": "paid"},
                        filters={"id": f"eq.{sess.get('id')}"} if sess.get("id")
                        else {"short_code": f"eq.{sess.get('short_code')}"})
    except Exception as e:  # noqa: BLE001
        logger.warning("clover settle: could not mark session paid: %s", e)

    phone = (sess.get("caller_phone") or "").strip()
    if phone:
        try:
            from ..sms.client import send_sms

            cur = (sess.get("currency") or "cad").upper()
            sym = "CA$" if cur == "CAD" else f"{cur} "
            await send_sms(phone, (
                f"Payment received \u2713 Your order is confirmed and paid — "
                f"{sym}{(sess.get('amount_cents') or 0) / 100:,.2f}. "
                "We'll have it ready shortly."))
        except Exception as e:  # noqa: BLE001 — receipt never blocks settlement
            logger.warning("clover settle: receipt SMS failed: %s", e)
