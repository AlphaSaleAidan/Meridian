"""Toast webhook signature verification.

Toast signs each webhook with HMAC-SHA256 over the raw request body, keyed by
the partner's webhook secret, and sends the result base64-encoded in the
``Toast-Signature`` header. See https://doc.toasttab.com/openapi/webhooks/

We verify in constant time and fail closed: a missing/garbled/mismatched
signature is rejected. The caller is responsible for the "secret not configured"
case (that should also fail closed before reaching here).
"""

from __future__ import annotations

import base64
import hashlib
import hmac


def compute_signature(secret: str, body: bytes) -> str:
    """Return the base64 HMAC-SHA256 of ``body`` under ``secret`` (Toast scheme)."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_signature(secret: str, body: bytes, provided_signature: str | None) -> bool:
    """Constant-time check of a Toast webhook signature.

    Returns False (reject) on any missing input or mismatch — never raises.
    """
    if not secret or not provided_signature:
        return False
    try:
        expected = compute_signature(secret, body)
    except Exception:
        return False
    return hmac.compare_digest(expected, provided_signature.strip())
