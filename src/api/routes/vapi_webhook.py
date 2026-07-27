"""
Vapi voice-agent webhook — production, multi-tenant.

Vapi (https://vapi.ai) replaces the Telnyx/Pipecat streaming voice agent. One
server URL handles every event; the merchant is resolved per call from the
dialed number, so a single Vapi number config serves all merchants.

Events handled:
  - assistant-request   → look up the merchant by dialed DID, return a dynamic
                          assistant (their menu/greeting + submit_order tool).
  - tool-calls / function-call (submit_order) → run the real order pipeline
                          (normalize → POS create → route = Stripe pay-link + SMS).
  - end-of-call-report  → log.

Phone-agent modules live in a sibling dir (same sys.path trick as
stripe_connect). They're dep-light (no pipecat), so the backend can import them.
build_system_prompt lives in pipecat-heavy bot.py, so the prompt is rebuilt here.
"""
import asyncio
import hmac
import json
import logging
import math
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ...services.phone_safety import (
    FORWARD_VERIFY_CALLER,
    map_ended_reason,
    normalize_e164,
    same_number,
)

logger = logging.getLogger("meridian.api.vapi")

router = APIRouter(prefix="/api/vapi", tags=["vapi"])

_PHONE_AGENT_DIR = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

WEBHOOK_URL = os.getenv("PUBLIC_PAY_BASE", "https://api.meridian.tips").rstrip("/") + "/api/vapi/webhook"

# Telnyx fallback: an existing Telnyx/Pipecat agent DID that Vapi forwards the
# call to when a merchant's voice ledger is underwater (revenue hasn't covered
# usage). Vapi's own card-on-file handles the GLOBAL float; this is the
# per-merchant policy gate. Disabled unless BOTH env vars are set — default is
# fail-open (always serve via Vapi).
# Shared secret Vapi sends as the `x-vapi-secret` header on every server request
# (set as server.secret on the assistant/phone-number). When set here, every
# inbound webhook must present it or it's rejected — closes the open-order hole.
# Unset → not enforced (safe rollout: deploy code, configure Vapi + this env,
# then enforcement turns on without a gap).
VAPI_SERVER_SECRET = os.getenv("VAPI_SERVER_SECRET", "").strip()

TELNYX_FALLBACK_NUMBER = os.getenv("TELNYX_FALLBACK_NUMBER", "").strip()
# Only forward when balance is at/below this many cents (negative = underwater).
# Unset → no gate. e.g. -2000 forwards once a merchant is $20 in the red.
_floor_raw = os.getenv("VOICE_BALANCE_FLOOR_CENTS", "").strip()
VOICE_BALANCE_FLOOR_CENTS = int(_floor_raw) if _floor_raw.lstrip("-").isdigit() else None

# Per-order fee = flat MERIDIAN_SERVICE_FEE_CENTS ($2.50). On top of that, calls
# longer than VOICE_INCLUDED_MIN minutes of AI time bill an overage of
# VOICE_OVERAGE_CENTS_PER_MIN ($0.45) per minute over the included block. The
# overage is computed at end-of-call (the order's Stripe fee is locked mid-call,
# before the duration is known), so it's tracked per-merchant in the voice ledger
# as billable revenue rather than added to the customer's order charge.
VOICE_INCLUDED_MIN = int(os.getenv("MERIDIAN_VOICE_INCLUDED_MIN", "3") or 3)
VOICE_OVERAGE_CENTS_PER_MIN = int(os.getenv("MERIDIAN_VOICE_OVERAGE_CENTS_PER_MIN", "45") or 45)
# Hard call cap: Vapi force-ends the call at this length (maxDurationSeconds on
# the assistant), so the worst case a merchant is billed per call is
# (cap − included) × overage — 5 min ⇒ 2 min over ⇒ 90¢ — and our own Vapi
# spend per call is capped with it. 0 disables the cap. This is the GLOBAL
# default; phone_agent_config.max_call_minutes overrides it per merchant
# (see _effective_cap_min).
VOICE_MAX_CALL_MIN = int(os.getenv("MERIDIAN_VOICE_MAX_CALL_MIN", "5") or 0)
# Grace past the advertised cap so a call that submits an order at ~4:55 still
# hears the spoken confirmation instead of dead air (order + SMS land either
# way). Billing is unaffected: the end-of-call overage is clamped to
# (cap − included) minutes, so the disclosed per-call maximum holds.
VOICE_CAP_GRACE_SEC = int(os.getenv("MERIDIAN_VOICE_CAP_GRACE_SEC", "15") or 0)

# Turn-taking tuning (startSpeakingPlan / stopSpeakingPlan) for every order
# assistant. Flag-gated OFF: these keys change live-call turn-taking on every
# merchant at once, and an unknown/renamed key on Vapi's side would fail the
# whole assistant — so flip MERIDIAN_VOICE_SPEECH_TUNING=1 only after one
# verified call on the test line. numWords=2 is the headline fix: it stops a
# caller's "yeah"/"uh-huh" backchannel from cutting the agent off mid-sentence.
VOICE_SPEECH_TUNING = (
    os.getenv("MERIDIAN_VOICE_SPEECH_TUNING", "").strip().lower() in ("1", "true", "yes")
)


def _speech_plans(config) -> dict:
    """startSpeakingPlan/stopSpeakingPlan keys for _assistant_for, or {} when
    the tuning flag is off (assistant payload stays byte-for-byte unchanged).

    Smart endpointing: LiveKit is Vapi's recommended EN-only provider; the
    multilingual wizard toggle (language=multi, Hindi/Punjabi code-switch)
    gets Vapi's own model instead so endpointing doesn't break mid-switch.
    """
    if not VOICE_SPEECH_TUNING:
        return {}
    lang = (getattr(config, "language", "") or "").strip().lower()
    provider = "vapi" if lang in ("multi", "multilingual") else "livekit"
    return {
        "startSpeakingPlan": {
            "waitSeconds": 0.4,
            "smartEndpointingPlan": {"provider": provider},
        },
        "stopSpeakingPlan": {
            # Ignore 1-word backchannels ("yeah", "okay") while the agent is
            # talking; a real interruption (2+ words) still stops it fast.
            "numWords": 2,
            "voiceSeconds": 0.2,
            "backoffSeconds": 1.0,
        },
    }


# ── merchant resolution ──────────────────────────────────────────────

def _dialed_number(msg: dict) -> str:
    """The Meridian DID the customer called (maps to a merchant)."""
    call = msg.get("call", {}) or {}
    for src in (call.get("phoneNumber"), msg.get("phoneNumber")):
        if isinstance(src, dict) and src.get("number"):
            return src["number"]
    return ""


def _caller_number(msg: dict) -> str:
    call = msg.get("call", {}) or {}
    cust = call.get("customer", {}) or msg.get("customer", {}) or {}
    return cust.get("number", "") if isinstance(cust, dict) else ""


async def _resolve_config(dialed: str):
    """MerchantPhoneConfig for the dialed DID; demo config if unmapped.

    NB: in prod Supabase IS configured, so get_merchant_config("demo") returns
    None (no 'demo' row) rather than the demo fallback — guard against that
    explicitly or submit_order crashes on a None config."""
    from merchant_config import get_merchant_by_phone, get_merchant_config, _demo_config
    merchant_id = (await get_merchant_by_phone(dialed)) if dialed else None
    cfg = await get_merchant_config(merchant_id) if merchant_id else None
    return cfg or _demo_config(merchant_id or "demo")


def _personality(config) -> dict:
    """Merchant-set agent personality (phone_agent_config.personality JSONB).

    {formality: float, upsell: 'none'|'gentle'|'active', humor: bool,
     customGreeting, customHold, customClosing, brandKeywords[]} — every field
    optional. Missing/None/non-dict → {} so the prompt stays byte-for-byte
    unchanged for merchants who never touched the panel."""
    p = getattr(config, "personality", None)
    return p if isinstance(p, dict) else {}


def _effective_greeting(config) -> str:
    """customGreeting (personality) overrides the standard greeting when set."""
    custom = str(_personality(config).get("customGreeting") or "").strip()
    return custom or (config.greeting or "")


def _personality_style_lines(p: dict) -> list[str]:
    """Prompt lines for the personality fields that are actually set."""
    lines: list[str] = []
    formality = p.get("formality")
    if isinstance(formality, (int, float)):
        if formality < 0.35:
            lines.append("- Keep the tone casual and relaxed.")
        elif formality > 0.7:
            lines.append("- Keep the tone polished and professional.")
    if p.get("humor") is True:
        lines.append("- Light, tasteful humor is welcome.")
    hold = str(p.get("customHold") or "").strip()
    if hold:
        lines.append(f'- When you need a moment say: "{hold}"')
    closing = str(p.get("customClosing") or "").strip()
    if closing:
        lines.append(f'- End calls with: "{closing}"')
    keywords = [str(k).strip() for k in (p.get("brandKeywords") or []) if str(k).strip()]
    if keywords:
        lines.append(
            "- Work these phrases in naturally when relevant: " + ", ".join(keywords)
        )
    return lines


# Step 3 of the call flow — the upsell instruction. 'gentle' (the default,
# and any unset/unknown value) keeps the original single-suggestion step;
# 'none' REPLACES it with a hard no-upsell rule; 'active' allows two.
_UPSELL_STEP_GENTLE = (
    "3. Once the caller finishes ordering, check whether they have added a drink or a side. "
    "If not, offer ONE natural upsell — e.g. 'Can I throw in a drink or a side for you?' "
    "Do this ONCE only; move on if they decline.\n"
)
_UPSELL_STEP_NONE = (
    "3. Do not upsell — never suggest additional items. Once the caller finishes "
    "ordering, move straight on.\n"
)
_UPSELL_STEP_ACTIVE = (
    "3. Once the caller finishes ordering, you may suggest add-ons that pair well "
    "(a drink, side, or dessert) — up to TWO natural suggestions per call, never "
    "pushy; move on as soon as they decline.\n"
)


def _upsell_step(p: dict) -> str:
    upsell = str(p.get("upsell") or "").strip().lower()
    if upsell == "none":
        return _UPSELL_STEP_NONE
    if upsell == "active":
        return _UPSELL_STEP_ACTIVE
    return _UPSELL_STEP_GENTLE


def _menu_block(config) -> str:
    """The prompt's MENU (+ SOLD OUT) block — shared by the legacy prompt and
    every script pack, so pricing/sold-out behavior never varies by pack."""
    menu_lines: list[str] = []
    if getattr(config, "menu_items", None):
        for it in config.menu_items:
            name = it.get("name", "item")
            size_prices: dict = it.get("size_prices") or {}
            price = it.get("price")
            topping_price = it.get("topping_price")
            sizes: list = it.get("sizes") or []
            modifications: list = it.get("modifications") or []

            if size_prices:
                # Per-size pricing (e.g. pizzas): "medium $14 / large $18 (+$2/topping)"
                price_parts = [
                    f"{s} ${size_prices[s]:.0f}"
                    for s in sizes
                    if s in size_prices
                ]
                line = f"- {name}: {' / '.join(price_parts)}"
                if topping_price:
                    line += f" (+${topping_price:.0f}/topping)"
            elif price:
                line = f"- {name}: ${float(price):.2f}"
                if sizes:
                    line += f" (sizes: {', '.join(sizes)})"
            else:
                line = f"- {name}"
                if sizes:
                    line += f" (sizes: {', '.join(sizes)})"

            if modifications:
                line += f" [options: {', '.join(modifications)}]"
            menu_lines.append(line)

    menu = ("\n\nMENU:\n" + "\n".join(menu_lines)) if menu_lines else ""

    # SOLD OUT section (menu store): items are EXCLUDED from the menu above
    # (never offered) but the agent must know they exist — if a caller asks
    # for one, apologize instead of treating it as off-menu.
    sold_out = [str(n).strip()
                for n in (getattr(config, "sold_out_items", None) or [])
                if str(n).strip()]
    if sold_out:
        menu += (
            "\n\nSOLD OUT TODAY (do NOT offer these; if the caller asks for one, "
            "apologize, say it's sold out today, and suggest a similar item):\n"
            + "\n".join(f"- {n}" for n in sold_out)
        )
    return menu


def _display_order_types(config) -> list[str]:
    """order_types for display — "dine_in" was renamed to "reservation" in the
    product; old configs persist."""
    raw_types = list(getattr(config, "order_types", ["pickup", "delivery"]))
    return ["reservation" if t == "dine_in" else t for t in raw_types]


def _reservation_block(config, display_types: list[str]) -> str:
    """RESERVATIONS prompt lines — shared by the legacy prompt and every
    script pack. "" when reservations aren't an order type."""
    reservation_lines = ""
    if "reservation" in display_types:
        resv = getattr(config, "reservation_config", None) or {}
        if resv.get("on_website") and resv.get("website_url"):
            reservation_lines = (
                "\nRESERVATIONS: If the caller wants a reservation, tell them the fastest way "
                f"is to book online at {resv['website_url']} — offer to take their name, party "
                "size, and preferred time as a backup if they'd rather book by phone."
            )
        else:
            reservation_lines = (
                "\nRESERVATIONS: If the caller wants a reservation, take it on the call: get "
                "their name, party size, date and time, and phone number. Confirm the details "
                "back, then call submit_order with order_type 'reservation' and the details in "
                "the notes."
            )
    return reservation_lines


def _transfer_block(transfer_number: str) -> str:
    """TRANSFER TO A HUMAN prompt block — shared by the legacy prompt and
    every script pack. Only rendered when the caller passed a validated
    transfer number (see _safe_transfer_number / the assistant-request
    handler), so merchants without one keep the prompt unchanged."""
    if not transfer_number:
        return ""
    return (
        "\n\nTRANSFER TO A HUMAN:\n"
        "- If the caller asks for a person or a manager, has a complaint, or a "
        "question you can't answer, say \"One moment — connecting you to the team.\" "
        "and use the transferCall tool.\n"
        "- If the transfer fails or nobody picks up, apologize, take a message — "
        "their name, phone number, and what they need — promise a callback, then "
        "resume the order if they still want it, or end the call politely.\n"
        "- Never attempt more than one transfer per call."
    )


def _resolve_script_pack(config) -> str | None:
    """The merchant's selected script pack id, or None for the legacy prompt.

    STRICTLY fail-legacy: any problem in the pack layer (module missing,
    unknown/typo'd id, NULL column) resolves to None so a live call always
    has the proven generic prompt as its floor.
    """
    try:
        from script_packs import resolve_pack_id
        return resolve_pack_id(getattr(config, "script_pack", None))
    except Exception:  # noqa: BLE001 — pack selection never breaks a call
        return None


def _pack_system_prompt(pack_id: str, config, transfer_number: str) -> str:
    """System prompt for a selected script pack (see script_packs.compose).

    The merchant-level blocks (menu/sold-out, personality style, reservations,
    transfer, menu link, cap pacing) are rendered with the SAME helpers the
    legacy prompt uses, so every safety/billing feature behaves identically
    regardless of pack — packs only change the CALL FLOW + extra guard lines.
    """
    from script_packs import PromptContext, compose
    personality = _personality(config)
    display_types = _display_order_types(config)
    style_lines = _personality_style_lines(personality)
    ctx = PromptContext(
        business_name=config.business_name,
        greeting=_effective_greeting(config),
        order_types=", ".join(display_types),
        has_delivery="delivery" in display_types,
        upsell_mode=str(personality.get("upsell") or "").strip().lower(),
        multilingual=(getattr(config, "language", "") or "").strip().lower()
        in ("multi", "multilingual"),
    )
    return compose(
        pack_id,
        ctx,
        style_block=("\n\nSTYLE:\n" + "\n".join(style_lines)) if style_lines else "",
        reservation_lines=_reservation_block(config, display_types),
        transfer_block=_transfer_block(transfer_number),
        menu_link_line=_menu_link_line(config),
        pacing_line=_pacing_line(_effective_cap_min(config)),
        menu_block=_menu_block(config),
    )


def _system_prompt(config, transfer_number: str = "") -> str:
    """Build a polished, money-flow-showcasing call script for any merchant.

    SCRIPT PACKS: when phone_agent_config.script_pack selects a known pack,
    the prompt is composed by script_packs.compose (per-vertical,
    time-optimized CALL FLOW; same guard rules and merchant blocks). NULL /
    "legacy" / unknown values — and ANY error in the pack layer — fall
    through to the legacy prompt below, byte-for-byte unchanged
    (tests/api/test_script_packs.py holds golden snapshots proving it).

    Improvements over the previous version:
    - Renders size_prices correctly so per-size items (e.g. pizzas) show real
      prices instead of $0.00.
    - Adds ONE suggestive upsell if the caller hasn't added a drink or side.
    - Explicitly collects the delivery address when order_type == delivery.
    - Instructs the assistant to read back the complete order with the total
      before calling submit_order.
    - Tells the caller about the pay-by-text link + receipt after the order
      is placed, making the full money flow visible in every demo call.
    """
    pack_id = _resolve_script_pack(config)
    if pack_id:
        try:
            return _pack_system_prompt(pack_id, config, transfer_number)
        except Exception as e:  # noqa: BLE001 — packs never break a call
            logger.error("script pack '%s' failed for merchant %s — legacy prompt: %s",
                         pack_id, getattr(config, "merchant_id", "?"), e)

    menu = _menu_block(config)
    display_types = _display_order_types(config)
    order_types = ", ".join(display_types)
    business = config.business_name
    reservation_lines = _reservation_block(config, display_types)

    # Merchant personality: tone/humor/custom-phrase lines only when set, so
    # an absent or empty personality leaves the prompt byte-for-byte unchanged.
    personality = _personality(config)
    style_lines = _personality_style_lines(personality)
    style_block = ("\n\nSTYLE:\n" + "\n".join(style_lines)) if style_lines else ""

    transfer_block = _transfer_block(transfer_number)

    return (
        f"You are the AI phone order-taker for {business}.\n"
        "Keep every reply to 1-2 sentences — warm, friendly, phone-natural. Never robotic."
        f"{style_block}\n\n"
        "CALL FLOW (follow this order every time):\n"
        f"1. Greet: \"{_effective_greeting(config)}\"\n"
        "2. Take the order item by item. For each item confirm: name, size (if applicable), "
        "quantity, and any extra toppings or modifications.\n"
        f"{_upsell_step(personality)}"
        "4. Ask how they'd like it (pickup, delivery — or a reservation if they're booking a table). Get their name.\n"
        "5. If delivery: ask for their delivery address before proceeding.\n"
        "6. Calculate the total (size price + per-topping charge × number of toppings for each "
        "item, then add sides and drinks). Read back the COMPLETE order — every item, size, "
        "and toppings — with the total, then ask 'Does that all look right?'\n"
        f"{_cash_offer_step(config)}"
        "7. Call submit_order ONLY after the customer confirms the order is correct.\n"
        "8. After submit_order returns, tell the caller: 'I've sent a secure payment link to "
        "your phone — you'll get a receipt once it goes through.'\n\n"
        "GUARD RULES:\n"
        f"- Available order types: {order_types}.\n"
        f"{reservation_lines}"
        f"{_cash_guard_line(config)}"
        "- Delivery without an address → ask for the address before calling submit_order.\n"
        "- Off-menu items → say so warmly and suggest a similar item.\n"
        "- Mishear → ask the caller to repeat just THAT item; never restart the order from scratch.\n"
        "- Frustrated caller → brief apology, repeat back only the unclear part, ask once to clarify."
        f"{_menu_link_line(config)}"
        f"{_pacing_line(_effective_cap_min(config))}"
        f"{transfer_block}"
        f"{menu}"
    )


def _effective_cap_min(config) -> int:
    """Effective hard call cap in minutes for this merchant.

    phone_agent_config.max_call_minutes overrides the env default when set
    (0 = explicitly uncapped for this merchant); NULL/absent falls back to
    VOICE_MAX_CALL_MIN. Every consumer of the cap — maxDurationSeconds, the
    spoken pacing line, and the end-of-call overage CLAMP — must use this same
    value or the disclosed per-call billing maximum breaks.
    """
    v = getattr(config, "max_call_minutes", None)
    if isinstance(v, int) and not isinstance(v, bool) and v >= 0:
        return v
    return VOICE_MAX_CALL_MIN


def _overage_minutes(dur_min: float, included_min: int, cap_min: int) -> int:
    """Billable whole minutes over the included block, clamped to the cap.

    With a hard cap the overage can never exceed (cap − included) minutes, so
    the bill holds to the disclosed maximum even when the drop lands a
    rounding-minute past the cap (grace period). cap_min <= 0 = uncapped.
    """
    over = max(0, math.ceil(dur_min) - included_min)
    if cap_min > 0:
        over = min(over, max(cap_min - included_min, 0))
    return over


def _menu_link_line(config) -> str:
    """One guard-rule line when the merchant has a published hosted menu page
    (merchant_menus.public_slug → meridian.tips/m/{slug}). Absent → "" so the
    prompt stays byte-for-byte unchanged for merchants without one."""
    url = (getattr(config, "menu_public_url", "") or "").strip()
    if not url:
        return ""
    return (
        f"\n- The full menu is online at {url} — if the caller asks to see the "
        "menu or asks for it to be texted, tell them that address clearly "
        "(say it once, slowly)."
    )


def _cash_offer_step(config) -> str:
    """CALL FLOW step: offer cash — ONLY when the merchant enabled accept_cash.

    Off/absent → "" so the prompt is byte-for-byte unchanged for every merchant
    that hasn't opted in behind the warning modal. When on, the agent asks how
    the caller wants to pay and passes pay_choice='cash' on submit_order for a
    cash order (unpaid, pay-on-pickup — no payment link is texted)."""
    if not getattr(config, "accept_cash", False):
        return ""
    return (
        "6b. Ask how they'd like to pay: pay now by secure text link, or CASH on "
        "pickup. If they choose cash, set pay_choice to 'cash' on submit_order — "
        "no payment link is sent and they pay at the counter.\n"
    )


def _cash_guard_line(config) -> str:
    """GUARD RULE reminder that cash is a valid choice — only when enabled."""
    if not getattr(config, "accept_cash", False):
        return ""
    return (
        "- Cash is accepted: if the caller wants to pay cash on pickup, take the "
        "order normally and set pay_choice='cash' — don't send a payment link.\n"
    )


def _pacing_line(cap_min: int) -> str:
    """When a hard call cap is set, tell the agent so it lands the order before
    Vapi force-ends the call — read back and submit rather than getting dropped
    mid-confirmation. Vapi has no mid-call timer webhook, so this prompt line is
    the lever: the agent must SAY a heads-up as the cap approaches instead of
    the caller being dropped cold."""
    if cap_min <= 0:
        return ""
    return (
        f"\n- Calls end automatically at {cap_min} minutes. Keep the order moving; "
        "if the call is running long, skip the upsell, read back the order, and submit it "
        "before time runs out. As the call approaches the limit, give the caller a brief "
        "spoken heads-up — e.g. \"we're almost out of time — let me read your order back\" — "
        "so the call never just cuts off on them."
    )


# Merchants pick a kokoro-style voice id in Phone Orders settings (stored on
# phone_agent_config.voice). Vapi only serves its own native voices, so map
# each UI id to the closest Vapi voice. Unknown/empty → Elliot. Configs
# default to af_bella, so unpicked merchants move Elliot → Savannah — matching
# the female "Bella" their settings UI has claimed all along.
# Live roster only — Lily/Hana/Paige/Cole/Spencer/Neha/Harry were RETIRED by
# Vapi (docs.vapi.ai/providers/voice/vapi-voices); a retired voiceId fails the
# call. Sample audio for each ships at frontend/public/voices/<name>.mp3.
KOKORO_TO_VAPI = {
    "af_bella": "Savannah",
    "af_sarah": "Layla",
    "af_nicole": "Naina",
    "bf_emma": "Emma",
    "am_adam": "Sid",
    "am_michael": "Elliot",
    "am_echo": "Kai",
    "bm_george": "Neil",
}

# The live Vapi roster (accents per docs.vapi.ai/providers/voice/vapi-voices):
# Savannah/Layla American F · Naina Indian F · Emma Asian-American F ·
# Elliot Canadian M · Kai/Sid American M · Neil Indian M. The accent picker in
# the setup wizard writes these names directly to phone_agent_config.voice.
VAPI_LIVE_VOICES = {"Savannah", "Layla", "Naina", "Emma", "Sid", "Elliot", "Kai", "Neil"}


def _vapi_voice(voice_id: str) -> str:
    v = (voice_id or "").strip()
    if v in VAPI_LIVE_VOICES:
        return v
    if v.title() in VAPI_LIVE_VOICES:  # tolerate "naina" from the UI
        return v.title()
    return KOKORO_TO_VAPI.get(v, "Elliot")


def _transcriber_for(config) -> dict:
    """Deepgram nova-3; language=multi enables code-switch understanding
    (Hindi/Punjabi + English on one call) — set by the wizard's multilingual
    toggle under the Indian accent group. Default stays EN-only."""
    t = {"provider": "deepgram", "model": "nova-3"}
    lang = (getattr(config, "language", "") or "").strip().lower()
    if lang in ("multi", "multilingual"):
        t["language"] = "multi"
    return t


_SUBMIT_ORDER_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_order",
        "description": "Call ONLY after the customer confirms the complete order is correct.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "order_type": {"type": "string", "enum": ["pickup", "delivery", "dine_in", "reservation"]},
                "items": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "quantity": {"type": "integer"},
                    "size": {"type": "string"},
                    "modifications": {"type": "array", "items": {"type": "string"}},
                }, "required": ["name", "quantity"]}},
                "delivery_address": {"type": "string"},
                "pay_choice": {
                    "type": "string",
                    "enum": ["pay_now", "pay_at_pickup", "cash"],
                    "description": "How the caller chose to pay. Set 'cash' ONLY "
                    "when the merchant accepts cash and the caller wants to pay "
                    "cash on pickup (no payment link is sent). Omit otherwise.",
                },
            },
            "required": ["customer_name", "order_type", "items"],
        },
    },
    "server": {"url": WEBHOOK_URL},
}


def _safe_transfer_number(config) -> str:
    """The merchant's transfer number, normalized — or "" when unset OR when it
    would guarantee a loop (equals the merchant's own agent DID). The async
    fleet-wide DID check lives in the assistant-request handler; this is the
    synchronous last line of defence used when no override is passed in."""
    transfer = normalize_e164(getattr(config, "transfer_number", "") or "")
    if not transfer:
        return ""
    if same_number(transfer, getattr(config, "phone_number", "") or ""):
        logger.error("transfer_number equals the agent DID for merchant %s — "
                     "suppressing transfer tool (loop guard)",
                     getattr(config, "merchant_id", "?"))
        return ""
    return transfer


def _transfer_tool(number: str) -> dict:
    """Vapi native transferCall tool — minimal shape, one destination."""
    return {
        "type": "transferCall",
        "destinations": [{
            "type": "number",
            "number": number,
            "message": "One moment — connecting you to the team.",
        }],
    }


def _assistant_for(config, transfer_number: str | None = None) -> dict:
    # personality.customGreeting (when set) overrides the standard greeting as
    # the spoken opener; _system_prompt's step-1 greet line uses the same value
    # so the prompt never contradicts what the caller just heard.
    #
    # transfer_number: None → derive from config (own-DID loop guard applied);
    # "" → explicitly suppress (the handler found the number is a fleet agent
    # DID); non-empty → use as given (already validated by the handler).
    if transfer_number is None:
        transfer_number = _safe_transfer_number(config)
    tools = [_SUBMIT_ORDER_TOOL]
    if transfer_number:
        tools.append(_transfer_tool(transfer_number))
    assistant = {
        "name": f"{config.business_name} — Order Taker",
        "firstMessage": _effective_greeting(config) or f"Thanks for calling {config.business_name}! What can I get for you?",
        "transcriber": _transcriber_for(config),
        "voice": {"provider": "vapi", "voiceId": _vapi_voice(getattr(config, "voice", "") or "")},
        "model": {"provider": "openai", "model": "gpt-4.1",
                  "messages": [{"role": "system", "content": _system_prompt(config, transfer_number)}],
                  "tools": tools},
        "endCallFunctionEnabled": True,
    }
    assistant.update(_speech_plans(config))
    cap_min = _effective_cap_min(config)
    if cap_min > 0:
        # Vapi drops the call at the cap (+ a short grace so the confirmation
        # sentence isn't cut mid-word); the prompt pacing line in
        # _system_prompt keeps the agent moving so orders land before it.
        assistant["maxDurationSeconds"] = cap_min * 60 + VOICE_CAP_GRACE_SEC
    return assistant


def _loop_guard_assistant(config) -> dict:
    """Assistant served when a forwarding loop is detected on the call.

    No submit_order and no transfer tool — the only job is to apologize, take
    the caller's name/number/message, and promise a callback. Anything else
    (ordering, transferring) would feed the loop or confuse the caller."""
    business = getattr(config, "business_name", "") or "this business"
    prompt = (
        f"You answer the phone for {business}. A phone-routing loop was detected on "
        "this call, so you CANNOT take an order and CANNOT transfer the call right now.\n"
        "1. Apologize briefly — the ordering line is having a routing hiccup.\n"
        "2. Take a message: the caller's name, the best number to call them back on, "
        "and what they need.\n"
        "3. Read the message back, promise the team will call them back shortly, and "
        "end the call politely.\n"
        "Never mention technical details or 'loops'. Keep every reply to 1-2 sentences."
    )
    return {
        "name": f"{business} — Message Taker",
        "firstMessage": (
            f"Thanks for calling {business}! Our ordering line is having a hiccup right "
            "now — can I take your name and number so the team can call you right back?"
        ),
        "transcriber": _transcriber_for(config),
        "voice": {"provider": "vapi", "voiceId": _vapi_voice(getattr(config, "voice", "") or "")},
        "model": {"provider": "openai", "model": "gpt-4.1",
                  "messages": [{"role": "system", "content": prompt}],
                  "tools": []},
        "endCallFunctionEnabled": True,
        "maxDurationSeconds": 120,
    }


def _inactive_assistant(config) -> dict:
    """Answer for a number whose merchant is cancelled/inactive: say the line
    isn't active and end. Never takes an order (the account isn't paying)."""
    return {
        "name": "Meridian — Inactive Line",
        "firstMessage": "Thanks for calling. This number isn't active for "
                        "ordering right now. Goodbye!",
        "voice": {"provider": "vapi", "voiceId": _vapi_voice(getattr(config, "voice", "") or "")},
        "model": {"provider": "openai", "model": "gpt-4.1",
                  "messages": [{"role": "system", "content":
                                "This phone line is not active. Briefly say it isn't "
                                "available for ordering and end the call. Take no orders."}],
                  "tools": []},
        "endCallFunctionEnabled": True,
        "maxDurationSeconds": 15,
    }


def _forwarding_verified_assistant(config) -> dict:
    """Minimal assistant answering our own forwarding-verification test call:
    confirm out loud and hang up — the DB row is already marked verified."""
    return {
        "name": "Meridian — Forwarding Check",
        "firstMessage": "Forwarding verified — you're all set. Goodbye!",
        "voice": {"provider": "vapi", "voiceId": _vapi_voice(getattr(config, "voice", "") or "")},
        "model": {"provider": "openai", "model": "gpt-4.1",
                  "messages": [{"role": "system", "content":
                                "This is an automated forwarding test call. Say goodbye "
                                "briefly and end the call. Do not take orders."}],
                  "tools": []},
        "endCallFunctionEnabled": True,
        "maxDurationSeconds": 15,
    }


async def _is_loop_caller(caller: str, dialed: str, config) -> bool:
    """Runtime loop detection: is the INBOUND caller one of our own agent DIDs?

    A legit customer never calls FROM an agent DID; if the caller id equals the
    dialed DID itself, this merchant's DID, or any DID in phone_agent_config,
    the call has been forwarded back into the fleet (e.g. transfer → store line
    → *72 forward → agent). Callers own the try/except — this must fail open."""
    c = normalize_e164(caller)
    if not c:
        return False
    if same_number(c, dialed) or same_number(c, getattr(config, "phone_number", "") or ""):
        return True
    from merchant_config import get_merchant_by_phone
    owner = await get_merchant_by_phone(c)
    # "demo-merchant" is the unconfigured-Supabase fallback (returned for ANY
    # number), not a real DID match — never treat it as a loop.
    return bool(owner) and owner != "demo-merchant"


async def _complete_forwarding_verification(merchant_id: str) -> bool:
    """Mark the newest pending forwarding verification for this merchant as
    verified. True when a pending row existed. Callers own error handling."""
    from datetime import datetime, timezone
    from ...db import get_db
    db = get_db()
    rows = await db.select(
        "forwarding_verifications",
        filters={"merchant_id": f"eq.{merchant_id}", "status": "eq.pending"},
        order="started_at.desc",
        limit=1,
    )
    if not rows:
        return False
    await db.update(
        "forwarding_verifications",
        {"status": "verified", "verified_at": datetime.now(timezone.utc).isoformat()},
        filters={"id": f"eq.{rows[0]['id']}"},
    )
    logger.info("forwarding verified for merchant %s (verification %s)",
                merchant_id, rows[0]["id"])
    return True


def _confirm(args: dict, routed: dict) -> str:
    items = args.get("items") or []
    n = sum(int(i.get("quantity", 1) or 1) for i in items)
    who = args.get("customer_name") or "there"
    otype = (args.get("order_type") or "pickup").replace("_", " ")
    base = f"Thanks {who}! Your {otype} order — {n} item{'s' if n != 1 else ''} — is in."
    if routed.get("sms_sent"):
        return (
            base
            + " I've sent a secure payment link to your phone"
            + " — you'll get a receipt once it goes through. See you soon!"
        )
    return base + " We'll have it ready for you shortly — see you soon!"


# POS leg statuses that mean the kitchen ticket actually landed (or was
# intentionally guarded on a demo/test merchant — not a real failure).
_REACHED_POS = {"sent", "demo_safe"}


def _order_reached(routed: dict) -> bool:
    """Did the placed order actually reach the merchant? Mirrors the honest
    Twilio path (phone.py:1129) — never read back a confirmation for an order
    that never landed.

      pay_now       → held by design (ticket deferred until payment); 'reached'
                      means the pay link was texted to the caller, or a demo
                      simulated the payment. Without it the caller can't pay and
                      no ticket is ever released.
      pay_at_pickup → released to the kitchen now; 'reached' means the POS ticket
                      pushed OR the merchant staff SMS went out. If neither, the
                      kitchen never sees the order.
      cash          → same as pay_at_pickup (no pay link by design).
    """
    mode = routed.get("mode", "")
    if mode == "pay_now":
        return bool(routed.get("sms_sent") or routed.get("simulated_paid"))
    delivery = routed.get("delivery") or {}
    # POS ticket landed (either the final pos_result reports success, or the
    # delivery leg does) OR the merchant staff SMS went out. A POS rejection
    # leaves pos_result.success False, so the honesty guarantee holds.
    pos_ok = (
        bool((routed.get("pos_result") or {}).get("success"))
        or (delivery.get("pos") or {}).get("status") in _REACHED_POS
    )
    merchant_ok = (delivery.get("merchant_sms") or {}).get("status") == "sent"
    return bool(pos_ok or merchant_ok)


def _order_failed_message(mode: str) -> str:
    """Honest, non-fabricated response when an order did not reach the merchant."""
    if mode == "pay_now":
        return ("I'm sorry — I wasn't able to get a payment link out to your "
                "phone just now, so your order isn't placed yet. Please give us "
                "a call back in a moment and we'll get it sorted.")
    return ("I'm so sorry — I'm having trouble sending your order to the kitchen "
            "right now, so it hasn't gone through. I've flagged it for the team. "
            "Please try calling back in a few minutes and we'll take care of you.")


async def _place_order(args: dict, config, caller_phone: str) -> str:
    """Run the real order pipeline via pay_on_phone.dispatch_order — POS push
    timing follows the payment mode: pay_now defers the ticket until Stripe
    confirms payment (mark_order_paid pushes it); pay_at_pickup pushes now."""
    from order_normalizer import normalize_order
    from pay_on_phone import dispatch_order
    if caller_phone and not args.get("caller_phone"):
        args["caller_phone"] = caller_phone
    normalized = normalize_order(args, config)
    # Off-menu items are DROPPED by the normalizer (never billed at $0.00) —
    # the agent must say so, and an order with nothing left must not dispatch.
    missing = normalized.get("unavailable_items") or []
    if normalized.get("is_empty"):
        # Nothing priceable to make — never dispatch a $0 order to the kitchen.
        if missing:
            names = " or ".join(missing[:3])
            return (f"I'm sorry — I couldn't find {names} on our menu, so I "
                    "haven't placed the order. Would you like to try something else?")
        return ("I didn't catch any items on that order — what would you like "
                "to get?")
    # the pay-link SMS only fires when the order carries caller_phone —
    # force it from the call's caller id so the SMS always goes out.
    if caller_phone:
        normalized["caller_phone"] = caller_phone
    routed = await dispatch_order(
        normalized, config, {"phone": caller_phone},
        pay_choice=args.get("pay_choice", ""),
    )
    routed = routed or {}
    pos_result = routed.get("pos_result", {})
    logger.info("VAPI order placed: merchant=%s caller=%s items=%d dropped=%d pos=%s sms=%s",
                config.merchant_id, caller_phone or "?", len(normalized.get("items", [])),
                len(missing), pos_result.get("success"), routed.get("sms_sent"))

    # Order integrity: never confirm an order that didn't actually reach the
    # merchant. If dispatch reported no delivery (POS reject on pay_at_pickup,
    # no pay link on pay_now, staff notification failed), apologize honestly and
    # flag it instead of fabricating "Your order is in" — same contract as the
    # Twilio path (phone.py:1129).
    if not _order_reached(routed):
        delivery = routed.get("delivery") or {}
        logger.error(
            "VAPI order NOT reached: merchant=%s caller=%s mode=%s pos=%s merchant_sms=%s sms_sent=%s",
            config.merchant_id, caller_phone or "?", routed.get("mode"),
            (delivery.get("pos") or {}).get("status"),
            (delivery.get("merchant_sms") or {}).get("status"),
            routed.get("sms_sent"),
        )
        return _order_failed_message(routed.get("mode", ""))

    confirm = _confirm({**args, "items": normalized.get("items", [])}, routed)
    if missing:
        names = " or ".join(missing[:3])
        confirm += (f" One thing — I couldn't find {names} on the menu, "
                    "so I left that off.")
    return confirm


@router.post("/webhook")
async def vapi_webhook(request: Request):
    # Auth: fail-CLOSED — if VAPI_SERVER_SECRET is unset the webhook is not
    # safe to process (any caller could trigger order placement). Return 503
    # so Vapi retries rather than accepting unauthenticated calls.
    if not VAPI_SERVER_SECRET:
        logger.error("vapi_webhook: VAPI_SERVER_SECRET not configured — refusing unauthenticated webhook")
        raise HTTPException(status_code=503, detail="Webhook authentication not configured")
    presented = request.headers.get("x-vapi-secret", "")
    if not hmac.compare_digest(presented, VAPI_SERVER_SECRET):
        logger.warning("vapi_webhook rejected: missing/invalid x-vapi-secret")
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    try:
        payload = await request.json()
    except Exception:
        return {"received": True}
    msg = (payload or {}).get("message", {}) or {}
    mtype = msg.get("type", "")

    # Inbound call → hand Vapi the merchant's dynamic assistant.
    if mtype == "assistant-request":
        try:
            dialed = _dialed_number(msg)
            caller = _caller_number(msg)
            config = await _resolve_config(dialed)

            # Forwarding-verification test call: our own Twilio caller-id
            # dialing the merchant's business line arrived here, so the
            # carrier forward works. Mark it verified and confirm out loud.
            if FORWARD_VERIFY_CALLER and caller and same_number(caller, FORWARD_VERIFY_CALLER):
                try:
                    merchant_id = getattr(config, "merchant_id", "") or ""
                    if merchant_id and await _complete_forwarding_verification(merchant_id):
                        return {"assistant": _forwarding_verified_assistant(config)}
                except Exception as e:  # noqa: BLE001 — verification never strands a call
                    logger.error("forwarding-verification check failed: %s", e)

            # Subscription gate: a cancelled merchant's number is reclaimed to
            # the pool (config cleared → this resolves to the demo fallback), but
            # in the window before reclaim — or if an account is flipped inactive
            # any other way — a real merchant whose agent is turned OFF must not
            # keep taking orders. Only gate a POSITIVELY-resolved real merchant
            # (not the demo fallback) whose `active` is explicitly False, so a
            # transient lookup miss never declines a paying merchant's call.
            _mid = getattr(config, "merchant_id", "") or ""
            if _mid and _mid != "demo" and getattr(config, "active", True) is False:
                logger.info("VAPI inactive gate: merchant=%s active=False — not serving orders", _mid)
                return {"assistant": _inactive_assistant(config)}

            # Runtime loop guard + transfer fleet check hit the same table and
            # are independent of each other, so they run CONCURRENTLY — one
            # round-trip of caller-hears-silence latency instead of two. Each
            # keeps its own fail-open contract (return_exceptions=True): a
            # loop-guard error serves the normal assistant; a fleet-check error
            # keeps the merchant's configured transfer.
            transfer = _safe_transfer_number(config)

            async def _loop_check() -> bool:
                # a caller id that IS one of our agent DIDs means the call has
                # been forwarded back into the fleet (transfer → store line →
                # full-forward → agent).
                return bool(caller) and await _is_loop_caller(caller, dialed, config)

            async def _fleet_check():
                # loop layer 3: a transfer number that is ANOTHER merchant's
                # agent DID would bounce callers around the fleet.
                if not transfer:
                    return None
                from merchant_config import get_merchant_by_phone
                return await get_merchant_by_phone(transfer)

            loop_hit, fleet_owner = await asyncio.gather(
                _loop_check(), _fleet_check(), return_exceptions=True)

            # Loop guard: serve the message-taker assistant instead of feeding
            # the loop. Fail-open on any error.
            if isinstance(loop_hit, BaseException):
                logger.error("loop-guard check failed (serving normal assistant): %s",
                             loop_hit)
            elif loop_hit:
                logger.error(
                    "VAPI LOOP GUARD: caller %s dialed %s (merchant=%s) is an agent "
                    "DID — forwarding loop detected, serving message-taker assistant. "
                    "Check this merchant's transfer_number / carrier forwarding.",
                    caller, dialed or "?", getattr(config, "merchant_id", "?"))
                return {"assistant": _loop_guard_assistant(config)}

            # Voice-ledger gate: if this merchant is underwater past the floor,
            # forward the call to the Telnyx/Pipecat agent instead of burning
            # Vapi minutes. Fail-open — any error/None balance serves via Vapi.
            # Per-location floor (migration 072): the merchant's own
            # voice_balance_floor_cents overrides the global env default, so each
            # operator sets their own self-funding tolerance. None on either ⇒
            # that layer is simply off.
            _floor = getattr(config, "voice_balance_floor_cents", None)
            if _floor is None:
                _floor = VOICE_BALANCE_FLOOR_CENTS
            if TELNYX_FALLBACK_NUMBER and _floor is not None:
                try:
                    from ...services.voice_ledger import balance_cents
                    bal = await balance_cents(getattr(config, "merchant_id", "") or "")
                    if bal is not None and bal <= _floor:
                        logger.info("VAPI fallback→Telnyx: merchant=%s balance=%d¢ floor=%d¢",
                                    config.merchant_id, bal, _floor)
                        return {"destination": {"type": "number", "number": TELNYX_FALLBACK_NUMBER}}
                except Exception as e:  # noqa: BLE001 — fallback check never strands the call
                    logger.error("voice-ledger fallback check failed: %s", e)

            # Transfer number fleet check result (gathered above): suppress the
            # transfer tool for this call when the number is another merchant's
            # agent DID. Fail-open: an error keeps the configured transfer.
            transfer_override: str | None = None
            if isinstance(fleet_owner, BaseException):
                logger.error("transfer fleet check failed (keeping transfer): %s",
                             fleet_owner)
            elif transfer and fleet_owner and fleet_owner != "demo-merchant":
                logger.error(
                    "transfer_number %s for merchant %s is agent DID of merchant "
                    "%s — suppressing transfer tool (loop guard)",
                    transfer, getattr(config, "merchant_id", "?"), fleet_owner)
                transfer_override = ""

            return {"assistant": _assistant_for(config, transfer_number=transfer_override)}
        except Exception as e:  # noqa: BLE001 — never strand the call
            logger.error("assistant-request failed: %s", e)
            return {"error": "Sorry, we couldn't connect your call. Please try again."}

    # Order submitted mid-call.
    if mtype in ("tool-calls",):
        results = []
        config = None
        for tc in msg.get("toolCallList", []) or msg.get("toolCalls", []) or []:
            fn = tc.get("function", {}) or {}
            args = fn.get("arguments", {}) or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            if fn.get("name") == "submit_order":
                try:
                    if config is None:
                        config = await _resolve_config(_dialed_number(msg))
                    res = await _place_order(args, config, _caller_number(msg))
                except Exception as e:  # noqa: BLE001
                    logger.error("submit_order failed: %s", e)
                    # Order integrity: the pipeline threw, so the order did NOT
                    # go through — never fabricate a confirmation.
                    res = ("I'm sorry — something went wrong placing that order, "
                           "so it hasn't gone through. Please give us a call back "
                           "in a moment and we'll get you taken care of.")
                results.append({"toolCallId": tc.get("id"), "result": res})
            else:
                results.append({"toolCallId": tc.get("id"), "result": "ok"})
        return {"results": results}

    if mtype == "function-call":  # legacy shape
        fc = msg.get("functionCall", {}) or {}
        if fc.get("name") == "submit_order":
            try:
                config = await _resolve_config(_dialed_number(msg))
                return {"result": await _place_order(fc.get("parameters", {}) or {}, config, _caller_number(msg))}
            except Exception as e:  # noqa: BLE001
                logger.error("submit_order (legacy) failed: %s", e)
                return {"result": ("I'm sorry — something went wrong placing that "
                                   "order, so it hasn't gone through. Please give "
                                   "us a call back in a moment.")}
        return {"result": "ok"}

    if mtype == "end-of-call-report":
        ended = msg.get("endedReason")
        # Vapi reports the all-in call cost (USD) + duration on the report message.
        call = msg.get("call", {}) or {}
        cost = msg.get("cost", call.get("cost"))
        call_id = call.get("id") or msg.get("callId") or ""
        dur_sec = (msg.get("durationSeconds") or call.get("durationSeconds")
                   or (msg.get("durationMinutes") or 0) * 60 or 0)
        dur_min = float(dur_sec) / 60.0
        logger.info("VAPI end-of-call: ended=%s cost=%s dur=%.1fmin call=%s",
                    ended, cost, dur_min, call_id)
        if not call_id:
            # The voice ledger dedupes on (source, ref) ONLY when a ref exists.
            # A retried report with no call id would double-bill, so synthesize
            # a stable ref from the payload — identical retries hash identically.
            import hashlib
            digest = hashlib.sha256(
                json.dumps(msg, sort_keys=True, default=str).encode()).hexdigest()
            call_id = f"noid-{digest[:16]}"
            logger.warning("end-of-call with no call id — synthesized ref %s", call_id)
        config = None
        try:
            dialed = _dialed_number(msg)
            config = await _resolve_config(dialed)
            merchant_id = getattr(config, "merchant_id", "") or "demo"
            if merchant_id == "demo":
                # Unmapped DID: the real merchant is NOT being metered. Bill
                # demo (visibility) but scream with the dialed number so ops
                # can map it and reattribute.
                logger.error("end-of-call for UNMAPPED number %s — costs booked "
                             "to 'demo' (call %s); map this DID to a merchant",
                             dialed or "?", call_id)
            from ...services.voice_ledger import credit, debit
            # Our cost (Vapi) — debit.
            cents = int(round(float(cost) * 100)) if cost is not None else 0
            if cents > 0:
                note = str(ended or "")
                if merchant_id == "demo" and dialed:
                    note = f"unmapped:{dialed} {note}".strip()
                await debit(merchant_id, cents, source="vapi_call",
                            ref=call_id, note=note)
            # Duration overage we bill the merchant: $0.45/min over 3 min (billed
            # per whole minute over the included block). Credit = billable revenue.
            # With a hard cap the overage is CLAMPED to (cap − included) so the
            # bill can never exceed the disclosed maximum, even when the drop
            # lands a rounding-minute past the cap. The clamp uses the SAME
            # per-merchant effective cap as maxDurationSeconds (a merchant with
            # a raised cap is billed to their cap, not the global one).
            # Fee parity: the merchant's provisioned billing terms
            # (merchant_billing_terms) override the env dials when present.
            # STRICTLY fail-open — any lookup problem bills the env defaults.
            included_min = VOICE_INCLUDED_MIN
            overage_rate = VOICE_OVERAGE_CENTS_PER_MIN
            if merchant_id != "demo":
                try:
                    from ...billing.fee_terms import get_active_terms
                    from ...db import get_db
                    terms = await get_active_terms(get_db(), merchant_id)
                    if terms:
                        if terms.get("included_call_min") is not None:
                            included_min = int(terms["included_call_min"])
                        if terms.get("call_overage_cents_per_min") is not None:
                            overage_rate = int(terms["call_overage_cents_per_min"])
                except Exception as terms_err:  # noqa: BLE001
                    logger.warning("billing-terms lookup failed for %s — env defaults: %s",
                                   merchant_id, terms_err)
            over_min = _overage_minutes(dur_min, included_min,
                                        _effective_cap_min(config))
            overage = over_min * overage_rate
            if overage > 0:
                await credit(merchant_id, overage, source="duration_overage",
                             ref=call_id, note=f"{over_min}min over @ {dur_min:.1f}min")
                logger.info("Duration overage billed: merchant=%s %dmin over → %d¢",
                            merchant_id, over_min, overage)
        except Exception as e:  # noqa: BLE001 — accounting never affects the call
            logger.error("voice_ledger end-of-call failed: %s", e)

        # Reason-code telemetry: one voice_call_endings row per call — the
        # instrument for "how many orders is the call cap killing".
        # config is passed through from the ledger block above so the merchant
        # isn't re-resolved (3 more Supabase round-trips) per report; if the
        # ledger block failed before resolving, the recorder resolves its own.
        try:
            await _record_call_ending(msg, call_id, ended, int(dur_sec or 0),
                                      config=config)
        except Exception as e:  # noqa: BLE001 — telemetry never affects the call
            logger.error("voice_call_endings record failed: %s", e)

    return {"received": True}


def _had_order(msg: dict) -> bool | None:
    """Best-effort: did a submit_order tool call land during this call?
    True/False when the report carries the conversation messages; None when
    it can't be determined from the payload."""
    artifact = msg.get("artifact") or {}
    messages = artifact.get("messages") or msg.get("messages")
    if not isinstance(messages, list):
        return None
    for m in messages:
        if not isinstance(m, dict):
            continue
        candidates = m.get("toolCalls") or []
        if m.get("name") == "submit_order":  # tool-result message shape
            return True
        for tc in candidates if isinstance(candidates, list) else []:
            fn = (tc or {}).get("function", {}) or {}
            if fn.get("name") == "submit_order":
                return True
    return False


async def _record_call_ending(msg: dict, call_id: str, ended: str | None,
                              duration_seconds: int, config=None) -> None:
    """Persist a voice_call_endings row (deduped on vapi_call_id for retries).

    ``config`` is the already-resolved MerchantPhoneConfig passed through from
    the end-of-call handler; None (e.g. the ledger block failed before
    resolving) falls back to resolving it here, exactly as before."""
    from ...db import get_db
    if config is None:
        config = await _resolve_config(_dialed_number(msg))
    merchant_id = getattr(config, "merchant_id", "") or "demo"
    db = get_db()
    if call_id:
        # Fast path for Vapi's serial retry (report re-sent after we already
        # recorded it). The true race — two concurrent retries both passing
        # this check — is closed by the partial unique index on vapi_call_id
        # (20260717_voice_call_endings_unique) + ignore-duplicates below.
        existing = await db.select(
            "voice_call_endings",
            filters={"vapi_call_id": f"eq.{call_id}"},
            limit=1,
        )
        if existing:
            return  # retried report — already recorded
    # ignore_duplicates (first write wins) with NO on_conflict target: the
    # vapi_call_id index is partial, which PostgREST's on_conflict inference
    # can't name — the losing concurrent insert resolves as a swallowed 409.
    await db.upsert("voice_call_endings", {
        "merchant_id": merchant_id,
        "vapi_call_id": call_id or None,
        "ended_reason": str(ended or "") or None,
        "disposition": map_ended_reason(ended),
        "duration_seconds": duration_seconds,
        "had_order": _had_order(msg),
    }, ignore_duplicates=True)
