"""
Phone-activation safety helpers.

Three concerns, all keyed on the same failure mode — a merchant's own phone
plumbing folding back on itself:

  1. Transfer-loop prevention. Scenario: the merchant sets transfer_number to
     their main store line, then full-forwards (*72) that line to their
     Meridian agent DID. "Transfer to a human" dials the store line → the
     carrier forwards it straight back to the agent → infinite loop, burning
     Vapi minutes and stranding the caller. `transfer_number_conflict` rejects
     that config at onboarding; the runtime loop guard in vapi_webhook catches
     anything that slips through.

  2. E.164 normalization shared by validation and runtime comparison, so
     "(555) 010-0100" and "+15550100100" are recognized as the same line.

  3. Vapi endedReason → disposition mapping for the voice_call_endings
     telemetry table ("how many orders is the call cap killing").
"""
import os

# Twilio caller-ID number used for forwarding verification test calls
# (Feature: forwarding setup wizard). When the wizard triggers verify-start we
# dial the merchant's business line FROM this number; if carrier forwarding is
# set up correctly the call arrives at the agent DID as an inbound Vapi
# assistant-request whose caller == this number — proof the forward works.
FORWARD_VERIFY_CALLER = os.getenv("MERIDIAN_FORWARD_VERIFY_CALLER", "").strip()


def normalize_e164(raw: str) -> str:
    """Best-effort E.164 normalization for North-American numbers.

    "" for empty/unparseable input. 10-digit → +1XXXXXXXXXX; 11-digit leading
    1 → +1XXXXXXXXXX; already-+ input keeps its country code with formatting
    stripped. Non-NANP digit strings pass through as +<digits> so two copies
    of the same international number still compare equal.
    """
    s = (raw or "").strip()
    if not s:
        return ""
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return ""
    if s.startswith("+"):
        return "+" + digits
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return "+" + digits


def same_number(a: str, b: str) -> bool:
    """True when a and b are the same phone line, format-insensitively."""
    na, nb = normalize_e164(a), normalize_e164(b)
    return bool(na) and na == nb


async def transfer_number_conflict(db, transfer_number: str, own_agent_did: str) -> str | None:
    """Merchant-readable rejection reason for a transfer number, or None if safe.

    Rejects when the transfer number is:
      - the merchant's own Meridian agent DID (guaranteed loop), or
      - ANY agent DID in phone_agent_config (another merchant's Meridian line
        would still bounce the caller around our fleet instead of reaching a
        person).

    `db` is the supabase REST client from get_db(); callers own error handling
    for db failures (a down DB should not silently approve a loop — let the
    exception surface as a 5xx).
    """
    norm = normalize_e164(transfer_number)
    if not norm:
        return None
    if same_number(norm, own_agent_did):
        return (
            "That transfer number is your Meridian agent line itself — "
            "transferring there would send callers straight back to the AI in a loop. "
            "Use a manager's cell or a back line instead, or keep your store line and "
            "set up conditional (busy / no-answer) forwarding so a human can still pick up."
        )
    rows = await db.select(
        "phone_agent_config",
        columns="merchant_id,phone_number",
        filters={"phone_number": f"eq.{norm}"},
        limit=1,
    )
    if rows:
        return (
            "That number is an AI agent line, so transfers would loop back to an AI "
            "instead of reaching a person. Use a manager's cell or a back line, or set up "
            "conditional (busy / no-answer) forwarding on your store line so a human can answer."
        )
    return None


# ── Vapi endedReason → disposition ───────────────────────────────────
# Raw endedReason values per docs.vapi.ai; anything unrecognized maps to
# "other" so a new Vapi reason string never breaks logging.
_DISPOSITION_BY_REASON = {
    "exceeded-max-duration": "cutoff",
    "customer-ended-call": "caller_hangup",
    "customer-busy": "caller_hangup",
    "customer-did-not-give-microphone-permission": "caller_hangup",
    "assistant-ended-call": "agent_hangup",
    "assistant-ended-call-after-message-spoken": "agent_hangup",
    "assistant-said-end-call-phrase": "agent_hangup",
    "assistant-forwarded-call": "agent_hangup",
    "silence-timed-out": "silence",
    "voicemail": "silence",
}

# Prefixes that indicate a platform/pipeline failure rather than a human choice.
_ERROR_PREFIXES = ("assistant-error", "pipeline-error", "call.start.error",
                   "assistant-not-found", "db-error", "unknown-error",
                   "vonage-", "twilio-", "phone-call-provider-")

DISPOSITIONS = ("cutoff", "caller_hangup", "agent_hangup", "silence", "error", "other")


def map_ended_reason(reason: str | None) -> str:
    """Map a raw Vapi endedReason to a stable disposition bucket."""
    r = (reason or "").strip().lower()
    if not r:
        return "other"
    if r in _DISPOSITION_BY_REASON:
        return _DISPOSITION_BY_REASON[r]
    for prefix in _ERROR_PREFIXES:
        if r.startswith(prefix):
            return "error"
    return "other"
