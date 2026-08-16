"""
Script pack COMPOSITION + selection — the logic half of the pack system.

A ScriptPack is a named, versioned set of conversation GUIDELINES (greeting
pattern, capture priorities, batching/confirm style, upsell policy, read-back
style) composed into a prompt alongside the shared non-negotiable HARD RULES.
Pack CONTENT lives in script_pack_defs.py; this module owns:

  - resolve_pack_id():  which pack (if any) a merchant config selects
  - PromptContext:      the merchant facts a pack's sections may vary on
  - compose():          pack sections → full system prompt
  - list_packs():       registry metadata for settings UIs

GUIDELINES, NOT SCRIPTS (Aidan, PR #346): pack content is rendered as
principles the agent adapts naturally to each conversation, not a numbered
flow it must recite. The things that must ALWAYS happen — read the complete
order back and get confirmation before submit_order, the pay-link line,
delivery-address / off-menu / mishear handling — are HARD RULES rendered
here for every pack, because those are product behavior, not style.

SELECTION CONTRACT (zero default-behavior change):
  phone_agent_config.script_pack NULL / "" / "legacy" / any unknown value
  → resolve_pack_id returns None → the caller (vapi_webhook._system_prompt)
  uses the untouched legacy prompt path, byte-for-byte identical to before
  this module existed. business_type is stored for UI recommendations only
  and NEVER auto-selects a pack.

SAFETY CONTRACT: every pack keeps the shared hard rules (read-back +
confirmation before submit, pay-link line, delivery address, off-menu,
mishear, frustrated caller) plus all merchant-level blocks the caller passes
in (style/personality, reservations, transfer-to-human, menu link, cap
pacing, menu + sold-out). Packs only ADD hard rules.

This module is imported standalone via sys.path (like merchant_config) and
must not import src.* — the caller renders the merchant-level blocks and
passes them in as strings.
"""
from __future__ import annotations

import os

from dataclasses import dataclass

from script_pack_defs import PACK_DEFS, ScriptPackDef

# The reserved id for the untouched generic prompt (the benchmark control).
LEGACY_PACK_ID = "legacy"


@dataclass(frozen=True)
class PromptContext:
    """Merchant facts a pack's sections are allowed to vary on."""
    business_name: str
    greeting: str
    order_types: str        # display string, e.g. "pickup, delivery"
    has_delivery: bool
    upsell_mode: str        # "" | "none" | "gentle" | "active" (merchant personality)
    multilingual: bool      # Deepgram language=multi transcriber is active


def resolve_pack_id(raw: object) -> str | None:
    """Selected pack id, or None for the legacy prompt path.

    None / "" / "legacy" / non-string / unknown ids ALL resolve to None so a
    typo'd or stale value can never change a live call's behavior — the worst
    case is always the proven legacy prompt.
    """
    if not isinstance(raw, str):
        return None
    pack_id = raw.strip().lower()
    if not pack_id or pack_id == LEGACY_PACK_ID:
        return None
    return pack_id if pack_id in PACK_DEFS else None


# ── trade → pack ─────────────────────────────────────────────────────
#
# The rep already chose the trade when they closed the deal, and it is stored
# on the organization. Making somebody ALSO pick a script pack by hand is how
# you end up where we were: twelve packs written, zero merchants using one.
#
# Keys are the pack keys from frontend/src/config/niches.ts, which is the same
# string organizations.business_type now holds.
TRADE_PACKS: dict[str, str] = {
    "restaurant": "restaurant_v1",
    "quickservice": "pizzeria_v1",
    "coffeeshop": "cafe_quickserve_v1",
    "barbershop": "barbershop_v1",
    "nails": "nails_v1",
    "medspa": "medspa_v1",
    "detailing": "detailing_v1",
    "mobiledetailing": "mobiledetailing_v1",
    "autoshop": "autoshop_v1",
    "smokeshop": "smokeshop_v1",
}


# The older vocabularies the same column still holds. Rep portals wrote a
# proposal DECK SLUG before the trade key existed, and Square detection writes
# its own BusinessType values — live data has all three. Same reconciliation
# the portal does in config/niches.ts; without it a merchant sold as "ca-qsr"
# silently gets no pack at all.
_TRADE_ALIASES: dict[str, str] = {
    "ca-qsr": "quickservice", "us-qsr": "quickservice", "fast_food": "quickservice",
    "ca-coffee": "coffeeshop", "us-coffee": "coffeeshop", "coffee_shop": "coffeeshop",
    "ca-salon": "barbershop", "us-salon": "barbershop", "barber_shop": "barbershop",
    "ca-nailsalon": "nails", "us-nailsalon": "nails", "nail_salon": "nails",
    "ca-spa": "medspa", "us-spa": "medspa", "med_spa": "medspa",
    "ca-detailing": "detailing", "us-detailing": "detailing",
    "ca-carwash": "detailing", "us-carwash": "detailing",
    "mobile_detailing": "mobiledetailing",
    "autoshop": "autoshop", "auto_shop": "autoshop",
    "ca-smokeshop": "smokeshop", "us-smokeshop": "smokeshop", "smoke_shop": "smokeshop",
}


def pack_for_trade(trade: object) -> str | None:
    """The pack this trade would use, benchmarked or not. None if unmapped."""
    if not isinstance(trade, str):
        return None
    key = trade.strip().lower()
    return TRADE_PACKS.get(_TRADE_ALIASES.get(key, key))


def auto_pack_for_trade(trade: object) -> str | None:
    """The pack to APPLY for a trade with no explicit choice — or None.

    THE TRADE'S PACK APPLIES, benchmarked or not (Aidan 2026-08-16, after I
    argued for gating it). The reasoning is sound: a barbershop answered by a
    prompt written for takeaway food is a worse call than one answered by an
    un-benchmarked barbershop prompt, and waiting for a bench run before any
    merchant sees a trade-specific script means none of them ever do.

    `status` therefore becomes information rather than a gate — the settings
    UI and the rep still see which packs have out-scored the control, and the
    bench still decides what we RECOMMEND. It no longer decides what runs.

    Two things stay, because this changes what a live agent says to a paying
    merchant's customers:
      · an explicit script_pack on the merchant always wins (see caller);
      · MERIDIAN_TRADE_PACK_AUTO=0 turns the whole behaviour off without a
        deploy, so a pack misbehaving on real calls is one env var from the
        proven legacy prompt rather than a release.
    """
    if os.environ.get("MERIDIAN_TRADE_PACK_AUTO", "1").strip().lower() in ("0", "false", "no"):
        return None
    return pack_for_trade(trade)


def get_pack(pack_id: str) -> ScriptPackDef:
    return PACK_DEFS[pack_id]


def list_packs() -> list[dict]:
    """Registry metadata for settings UIs (legacy control listed first)."""
    packs = [{
        "id": LEGACY_PACK_ID,
        "version": "1",
        "label": "Standard (current)",
        "recommend": "The default generic script — the control every pack is benchmarked against.",
        "status": "control",
    }]
    packs += [
        {"id": p.id, "version": p.version, "label": p.label,
         "recommend": p.recommend, "status": p.status}
        for p in PACK_DEFS.values()
    ]
    return packs


# Shared DELIVERY guidelines — how the agent *sounds*, appended after every
# pack's own guidelines (packs own the call flow; these own the feel). Kept
# out of HARD RULES on purpose: they're style principles the agent adapts,
# not product guarantees. Word choice matters for the upsell-override tests:
# never use the words "upsell" or "suggestion" here.
_SHARED_DELIVERY_GUIDELINES = [
    (
        "Vary your acknowledgments — 'got it', 'perfect', 'sure thing', "
        "'sounds good' — and never start two replies in a row with the same "
        "phrase."
    ),
    (
        "Ask ONE thing at a time. If you need two details, get the first, "
        "acknowledge it, then ask for the second — a reply with two questions "
        "in it forces the caller to remember both."
    ),
]

# Shared HARD RULES — non-negotiable product behavior, rendered for every
# pack. The first two carry the legacy prompt's read-back-then-submit and
# pay-link guarantees (steps there, hard rules here); the rest are the same
# protections as the legacy GUARD RULES block. Packs can only append.
_SHARED_HARD_RULES = (
    "- Before calling submit_order: read the COMPLETE order back — every item, "
    "size, and modifications — with the total, and ask 'Does that all look "
    "right?'. Call submit_order ONLY after the caller confirms it's correct.\n"
    "- After submit_order returns, tell the caller: 'I've sent a secure payment "
    "link to your phone — you'll get a receipt once it goes through.'\n"
    "- Delivery without an address → ask for the address before calling submit_order.\n"
    "- Off-menu items → say so warmly and suggest a similar item.\n"
    "- Mishear → ask the caller to repeat just THAT item; never restart the order from scratch.\n"
    "- Frustrated caller → brief apology, repeat back only the unclear part, ask once to clarify."
)


def compose(
    pack_id: str,
    ctx: PromptContext,
    *,
    style_block: str = "",
    reservation_lines: str = "",
    transfer_block: str = "",
    menu_link_line: str = "",
    pacing_line: str = "",
    menu_block: str = "",
    sms_consent_block: str = "",
    cash_block: str = "",
) -> str:
    """Compose a pack's guidelines + the shared hard rules into a prompt.

    Skeleton: persona line, STYLE, CONVERSATION GUIDELINES (the pack's
    adaptable principles), HARD RULES (non-negotiables, shared + pack
    extras), then the merchant-level blocks — so every downstream feature —
    personality, reservations, transfer, menu link, cap pacing, sold-out
    menu — behaves identically regardless of pack. The keyword blocks are
    rendered by the caller with the SAME helpers the legacy prompt uses.

    cash_block is "PAY WITH CASH" (migration 047) and belongs with the hard
    rules for the same reason as the consent block: it is a MERCHANT-level
    setting, not a pack's business. Without it, switching a merchant who
    accepts cash onto a pack silently stopped their agent offering it —
    exactly the failure the A2P disclosure had, found the same way, by a test
    that already existed.

    sms_consent_block is the A2P 10DLC verbal opt-in, and it belongs with the
    HARD RULES rather than the merchant blocks. It was missing entirely: the
    legacy prompt carried it and no pack did, so the day a merchant was moved
    onto a pack their agent would have started texting customers with none of
    the disclosure the Telnyx campaign is filed on — brand, frequency, rates,
    STOP, HELP, no-share. Nobody is on a pack yet, so nothing shipped that
    way; the point is that switching one on must not be able to drop it.
    """
    pack = get_pack(pack_id)
    guidelines = "\n".join(
        f"- {g}" for g in [*pack.guidelines(ctx), *_SHARED_DELIVERY_GUIDELINES]
    )
    extra_rules = pack.hard_rules(ctx)
    extra_rules_block = ("\n" + "\n".join(extra_rules)) if extra_rules else ""

    # ── the trade knowledge blocks ──────────────────────────────────────
    #
    # Rendered AFTER the hard rules and before the menu, so the agent reads
    # them as reference rather than as steps. Each is omitted entirely when a
    # pack does not define it — an empty heading is worse than no heading,
    # because the model will try to fill it.
    upsells = pack.upsells(ctx)
    upsell_block = ("\n\nWORTH OFFERING (once, by name, only when it genuinely "
                    "fits what they asked for — never a vague 'anything else?'):\n"
                    + "\n".join(f"- {u}" for u in upsells)) if upsells else ""

    faqs = pack.faqs(ctx)
    faq_block = ("\n\nWHAT CALLERS ASK (answer in ONE sentence, then carry on "
                 "with what you were doing):\n"
                 + "\n".join(f"- \"{q}\" → {a}" for q, a in faqs)) if faqs else ""

    objections = pack.objections(ctx)
    objection_block = ("\n\nIF THEY HESITATE (use the short handle, ONCE — a "
                       "second attempt is pressure, and pressure loses the "
                       "booking a single honest sentence would have kept):\n"
                       + "\n".join(f"- \"{o}\" → {h}" for o, h in objections)) if objections else ""

    return (
        f"You are the AI phone order-taker for {ctx.business_name}.\n"
        "Keep every reply to 1-2 sentences — warm, friendly, phone-natural. Never robotic."
        f"{style_block}\n\n"
        "CONVERSATION GUIDELINES (principles to adapt naturally — follow the "
        "caller's lead, don't recite a script):\n"
        f"{guidelines}\n\n"
        "HARD RULES (never bend these, whatever shape the conversation takes):\n"
        f"- Available order types: {ctx.order_types}.\n"
        # (legacy runs the reservation block straight into the next guard
        # line with no newline; packs are new text, so terminate it cleanly)
        f"{reservation_lines + chr(10) if reservation_lines else ''}"
        f"{_SHARED_HARD_RULES}"
        f"{cash_block}"
        f"{sms_consent_block}"
        f"{extra_rules_block}"
        f"{menu_link_line}"
        f"{pacing_line}"
        f"{transfer_block}"
        f"{upsell_block}"
        f"{faq_block}"
        f"{objection_block}"
        f"{menu_block}"
    )
