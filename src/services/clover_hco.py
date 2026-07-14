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
    """HCO host, following the same CLOVER_ENVIRONMENT / CLOVER_REGION
    convention as clover_api_base() (pos_connector.py / src/config.py):
    sandbox unless CLOVER_ENVIRONMENT=production. CLOVER_HCO_BASE overrides."""
    override = os.getenv("CLOVER_HCO_BASE", "")
    if override:
        return override.rstrip("/")
    if os.getenv("CLOVER_ENVIRONMENT", "sandbox") != "production":
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
