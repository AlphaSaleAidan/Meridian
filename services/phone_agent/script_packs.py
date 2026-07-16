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
) -> str:
    """Compose a pack's guidelines + the shared hard rules into a prompt.

    Skeleton: persona line, STYLE, CONVERSATION GUIDELINES (the pack's
    adaptable principles), HARD RULES (non-negotiables, shared + pack
    extras), then the merchant-level blocks — so every downstream feature —
    personality, reservations, transfer, menu link, cap pacing, sold-out
    menu — behaves identically regardless of pack. The keyword blocks are
    rendered by the caller with the SAME helpers the legacy prompt uses.
    """
    pack = get_pack(pack_id)
    guidelines = "\n".join(f"- {g}" for g in pack.guidelines(ctx))
    extra_rules = pack.hard_rules(ctx)
    extra_rules_block = ("\n" + "\n".join(extra_rules)) if extra_rules else ""

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
        f"{extra_rules_block}"
        f"{menu_link_line}"
        f"{pacing_line}"
        f"{transfer_block}"
        f"{menu_block}"
    )
