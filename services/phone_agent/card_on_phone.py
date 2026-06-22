"""
CARD ON THE PHONE — backup payment capture when the SMS pay-link can't be used.

The primary pay-now path texts a secure link (pay_on_phone.collect_pay_now). When
the caller has no textable mobile (landline, SMS send failed, or the carrier
rejects it), we fall back to taking the card *on the call* via the phone keypad
(DTMF), run it immediately, and tell the caller "approved" or "declined" before
they hang up — so the merchant never preps an unpaid order (anti-scam / anti
no-show, the whole point of pay-on-phone).

PCI NOTE (read before enabling real charges):
  Raw PAN entry over DTMF is PCI-DSS scope. For production this MUST run through a
  PCI-compliant DTMF-masking capture (Telnyx <Gather> payment masking or a
  tokenizing IVR) so the digits never reach our application logs or storage. This
  module keeps card data in memory ONLY for the duration of the charge, NEVER logs
  the PAN/CVV, and NEVER persists them. Real charging is OFF unless a gateway is
  explicitly configured (PHONE_CARD_GATEWAY=stripe + key); otherwise it runs in
  demo-safe SIMULATE mode so the whole flow is demonstrable without moving money.

Public surface:
  luhn_ok / card_brand / mask_pan / parse_expiry / valid_*   — validation helpers
  CardCapture + start_capture/get_capture/clear_capture       — per-call DTMF state
  charge(...)                                                  — pluggable gateway
  should_offer_card_fallback(...)                             — when to fall back
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

logger = logging.getLogger("meridian.phone_agent.card_on_phone")

# Master gate. The card-on-phone IVR is OFF until a merchant/host opts in, so
# wiring it into the call flow never changes live behavior unreviewed.
CARD_PAYMENT_ENABLED = os.getenv("PHONE_CARD_PAYMENT", "0").lower() in ("1", "true", "yes")

# Which real gateway to use when NOT in demo. Empty = simulate only (demo-safe).
CARD_GATEWAY = os.getenv("PHONE_CARD_GATEWAY", "").strip().lower()

DEMO_MERCHANT_ID = os.getenv("DEMO_MERCHANT_ID", "demo-merchant")

# In-memory capture TTL (seconds). A keypad payment that stalls past this is
# dropped so half-entered card data never lingers in memory.
_CAPTURE_TTL = int(os.getenv("PHONE_CARD_CAPTURE_TTL", "300"))
_MAX_ATTEMPTS = 2  # retries before we give up and offer pay-at-pickup / a human


# ─── Validation helpers ──────────────────────────────────────────────────────

def digits_only(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def luhn_ok(pan: str) -> bool:
    """Luhn checksum — catches typos/mis-keys before we ever call a gateway."""
    pan = digits_only(pan)
    if not 12 <= len(pan) <= 19:
        return False
    total = 0
    parity = len(pan) % 2
    for i, ch in enumerate(pan):
        d = ord(ch) - 48
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def card_brand(pan: str) -> str:
    """Best-effort brand from the leading digits (for the spoken confirmation)."""
    pan = digits_only(pan)
    if not pan:
        return "unknown"
    if pan[0] == "4":
        return "visa"
    two = int(pan[:2]) if len(pan) >= 2 else 0
    four = int(pan[:4]) if len(pan) >= 4 else 0
    if 51 <= two <= 55 or 2221 <= four <= 2720:
        return "mastercard"
    if two in (34, 37):
        return "amex"
    if pan[:4] == "6011" or two == 65:
        return "discover"
    return "unknown"


def mask_pan(pan: str) -> str:
    """Last-4 only — the ONLY form of the PAN we ever log or store."""
    pan = digits_only(pan)
    return f"•••• {pan[-4:]}" if len(pan) >= 4 else "••••"


def parse_expiry(raw: str) -> tuple[int, int] | None:
    """Accept MMYY (4 keypad digits). Returns (month, 2-digit-year) or None."""
    d = digits_only(raw)
    if len(d) != 4:
        return None
    mm, yy = int(d[:2]), int(d[2:])
    if not 1 <= mm <= 12:
        return None
    return mm, yy


def expiry_in_future(mm: int, yy: int, now: tuple[int, int] | None = None) -> bool:
    """True if MM/YY (2-digit year, 20YY) is the current month or later."""
    if now is None:
        t = time.gmtime()
        cur_y, cur_m = t.tm_year % 100, t.tm_mon
    else:
        cur_y, cur_m = now
    return (yy, mm) >= (cur_y, cur_m)


def valid_pan(pan: str) -> bool:
    return luhn_ok(pan)


def valid_cvv(cvv: str, brand: str = "") -> bool:
    d = digits_only(cvv)
    return len(d) == (4 if brand == "amex" else 3) or len(d) in (3, 4)


def valid_postal(postal: str) -> bool:
    # CA postal (6 alphanumeric) often keyed as digits, or US ZIP (5). Keep it
    # permissive: 3..6 keypad digits. AVS is advisory, not a hard gate here.
    return 3 <= len(digits_only(postal)) <= 6


# ─── Per-call capture state (in-memory, TTL'd, never logged) ──────────────────

@dataclass
class CardCapture:
    call_sid: str
    order_ref: str = ""          # phone_orders pos_order_id, for mark_order_paid
    merchant_id: str = ""
    amount_cents: int = 0
    caller_phone: str = ""
    pan: str = ""
    expiry: str = ""
    cvv: str = ""
    postal: str = ""
    attempts: int = 0
    created: float = field(default_factory=time.time)

    def expired(self) -> bool:
        return (time.time() - self.created) > _CAPTURE_TTL


_captures: dict[str, CardCapture] = {}


def _gc() -> None:
    for sid in [s for s, c in _captures.items() if c.expired()]:
        _captures.pop(sid, None)


def start_capture(call_sid: str, **kw) -> CardCapture:
    _gc()
    cap = CardCapture(call_sid=call_sid, **kw)
    _captures[call_sid] = cap
    return cap


def get_capture(call_sid: str) -> CardCapture | None:
    cap = _captures.get(call_sid)
    if cap and cap.expired():
        clear_capture(call_sid)
        return None
    return cap


def clear_capture(call_sid: str) -> None:
    """Wipe the in-memory card data the instant we're done with it."""
    cap = _captures.pop(call_sid, None)
    if cap:
        cap.pan = cap.cvv = cap.expiry = cap.postal = ""


# ─── Charge result + pluggable gateway ───────────────────────────────────────

@dataclass
class ChargeResult:
    approved: bool
    brand: str = "unknown"
    last4: str = ""
    txn_id: str = ""
    decline_reason: str = ""        # machine code: card_declined | expired_card | ...
    spoken: str = ""                # caller-facing sentence


# Deterministic test PANs for the demo-safe simulate path (standard gateway test
# numbers, so a demo is repeatable).
_SIM_DECLINES = {
    "4000000000000002": "card_declined",
    "4000000000009995": "insufficient_funds",
    "4000000000000069": "expired_card",
    "4000000000000127": "incorrect_cvc",
}


def _decline_sentence(reason: str) -> str:
    return {
        "invalid_number": "That card number didn't check out. Let's try again.",
        "expired_card": "That card looks expired. Do you have another card?",
        "insufficient_funds": "The card was declined for insufficient funds. Want to try another?",
        "incorrect_cvc": "The security code didn't match. Let's try once more.",
        "card_declined": "Sorry, that card was declined. Want to try a different card?",
    }.get(reason, "Sorry, that payment didn't go through. Want to try another card?")


async def charge(
    pan: str,
    expiry: str,
    cvv: str,
    postal: str,
    amount_cents: int,
    *,
    merchant_id: str = "",
    currency: str = "CAD",
    config=None,
) -> ChargeResult:
    """Run the card. Returns a ChargeResult — NEVER logs the PAN/CVV.

    Real charging only happens when CARD_GATEWAY is configured AND the merchant
    isn't the demo merchant. Otherwise we SIMULATE (demo-safe): Luhn + test-PAN
    table decide approve/decline so the entire flow is demonstrable end-to-end
    without moving money.
    """
    brand = card_brand(pan)
    last4 = digits_only(pan)[-4:]

    # Hard local validation first — cheap, and keeps junk off the gateway.
    if not luhn_ok(pan):
        return ChargeResult(False, brand, last4, decline_reason="invalid_number",
                            spoken=_decline_sentence("invalid_number"))
    exp = parse_expiry(expiry)
    if not exp or not expiry_in_future(*exp):
        return ChargeResult(False, brand, last4, decline_reason="expired_card",
                            spoken=_decline_sentence("expired_card"))

    use_real = bool(CARD_GATEWAY) and merchant_id != DEMO_MERCHANT_ID
    if not use_real:
        return _simulate(pan, brand, last4, amount_cents)

    try:
        if CARD_GATEWAY == "stripe":
            return await _charge_stripe(pan, exp, cvv, postal, amount_cents, currency, brand, last4)
        logger.error("Unknown PHONE_CARD_GATEWAY=%r — refusing to charge", CARD_GATEWAY)
        return ChargeResult(False, brand, last4, decline_reason="gateway_unavailable",
                            spoken="Our card system is unavailable right now.")
    except Exception as e:  # never leak card data in the error
        logger.error("Card charge errored (brand=%s last4=%s): %s", brand, last4, type(e).__name__)
        return ChargeResult(False, brand, last4, decline_reason="processing_error",
                            spoken="Sorry, we hit a snag charging that card.")


def _simulate(pan: str, brand: str, last4: str, amount_cents: int) -> ChargeResult:
    pan_d = digits_only(pan)
    reason = _SIM_DECLINES.get(pan_d)
    if reason:
        return ChargeResult(False, brand, last4, decline_reason=reason,
                            spoken=_decline_sentence(reason))
    txn_id = f"sim_{last4}_{int(time.time())}"
    return ChargeResult(
        True, brand, last4, txn_id=txn_id,
        spoken=f"Approved — your {brand if brand != 'unknown' else 'card'} ending {last4} "
               f"was charged. Your order's all set.",
    )


async def _charge_stripe(pan, exp, cvv, postal, amount_cents, currency, brand, last4) -> ChargeResult:
    """Thin Stripe PaymentIntents adapter (raw PAN).

    GATED: Stripe rejects raw card numbers unless the account is explicitly
    PCI-DSS enabled (`payment_method_data[card][number]` is off by default). This
    is here so the real wiring point is explicit; it is never reached unless
    PHONE_CARD_GATEWAY=stripe AND STRIPE_SECRET_KEY is set. Card data stays local.
    """
    import httpx
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        return ChargeResult(False, brand, last4, decline_reason="gateway_unavailable",
                            spoken="Our card system isn't set up yet.")
    mm, yy = exp
    data = {
        "amount": str(amount_cents),
        "currency": currency.lower(),
        "confirm": "true",
        "payment_method_data[type]": "card",
        "payment_method_data[card][number]": digits_only(pan),
        "payment_method_data[card][exp_month]": str(mm),
        "payment_method_data[card][exp_year]": str(2000 + yy),
        "payment_method_data[card][cvc]": digits_only(cvv),
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.stripe.com/v1/payment_intents",
            data=data, auth=(key, ""), timeout=20,
        )
    body = r.json()
    if r.status_code == 200 and body.get("status") == "succeeded":
        return ChargeResult(True, brand, last4, txn_id=body.get("id", ""),
                            spoken=f"Approved — your card ending {last4} was charged.")
    reason = (body.get("error", {}) or {}).get("code", "card_declined")
    return ChargeResult(False, brand, last4, decline_reason=reason,
                        spoken=_decline_sentence(reason))


# ─── When to fall back to the keypad ─────────────────────────────────────────

def should_offer_card_fallback(sms_sent: bool, payment_mode: str = "pay_now") -> bool:
    """Offer keypad card entry only when: the feature is enabled, the merchant
    wants pay-now, and the secure SMS link could NOT be delivered."""
    return CARD_PAYMENT_ENABLED and payment_mode == "pay_now" and not sms_sent


def attempts_exhausted(cap: CardCapture) -> bool:
    return cap.attempts >= _MAX_ATTEMPTS
