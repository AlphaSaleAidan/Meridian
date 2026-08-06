"""
Destination-aware SMS from-number selection.

All outbound SMS historically sent from the single ``TELNYX_PHONE_NUMBER``
(a US DID). Canadian numbers in the Telnyx account sit on their own messaging
profile and deliver fine, so the fix is to pick the from-number by DESTINATION
country: a Canadian DID for Canadian destinations, the existing global env for
everything else.

Canada and the US share the +1 NANP country code, so the country cannot be read
off the dial prefix — it has to come from the area code.

Every helper here is pure and fail-open: any unexpected input returns the
caller's existing default, so a bad number can never stop an SMS from sending.
"""
from __future__ import annotations

import os
import re

# NANP area codes assigned to Canada (NPAs, incl. recent overlays).
CANADIAN_AREA_CODES = frozenset(
    {
        "204", "226", "236", "249", "250", "263", "289", "306", "343", "354",
        "365", "367", "368", "382", "387", "403", "416", "418", "428", "431",
        "437", "438", "450", "468", "474", "506", "514", "519", "548", "579",
        "581", "584", "587", "604", "613", "639", "647", "672", "683", "705",
        "709", "742", "753", "778", "780", "782", "807", "819", "825", "867",
        "873", "879", "902", "905",
    }
)


def _nanp_area_code(destination: str) -> str | None:
    """Area code of a +1 NANP destination, or None if it isn't one.

    Accepts the shapes the send paths actually see: ``+15551234567``,
    ``15551234567``, ``5551234567``, and anything with punctuation.
    """
    digits = re.sub(r"\D", "", destination or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return digits[:3]


def is_canadian_destination(destination: str) -> bool:
    """True when ``destination`` is a +1 number on a Canadian area code."""
    try:
        return _nanp_area_code(destination) in CANADIAN_AREA_CODES
    except Exception:  # noqa: BLE001 — fail open: never block a send
        return False


def sms_from_number(destination: str, default: str | None = None) -> str:
    """Pick the from-number for an outbound SMS to ``destination``.

    Canadian destination + ``TELNYX_PHONE_NUMBER_CA`` set → the Canadian DID.
    Everything else (including any error) → ``default``, or
    ``TELNYX_PHONE_NUMBER`` when no default is given. Env is read at call time
    so tests and redeploys pick up changes without a re-import.
    """
    try:
        fallback = default if default is not None else os.getenv("TELNYX_PHONE_NUMBER", "")
        if is_canadian_destination(destination):
            ca = (os.getenv("TELNYX_PHONE_NUMBER_CA", "") or "").strip()
            if ca:
                return ca
        return fallback
    except Exception:  # noqa: BLE001 — fail open: never block a send
        return default if default is not None else os.getenv("TELNYX_PHONE_NUMBER", "")
