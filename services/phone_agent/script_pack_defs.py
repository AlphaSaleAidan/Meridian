"""
Script pack DEFINITIONS — per-vertical conversation GUIDELINES.

Data only: each pack is a ScriptPackDef whose sections (conversation
guidelines + extra hard rules) are small pure functions of the
PromptContext. The composition skeleton, selection rules, and the shared
non-negotiable rules live in script_packs.py — packs can NEVER remove a
hard rule, only add.

GUIDELINES, NOT SCRIPTS (Aidan, PR #346): a pack describes principles,
priorities, and patterns the agent adapts naturally to each conversation —
"prefer establishing pickup vs delivery early", "confirm items in small
batches rather than echoing every line" — never a rigid step sequence it
must recite. The non-negotiables (read-back + confirmation before
submit_order, the pay-link line, delivery-address / off-menu / pay-now
handling) are HARD RULES rendered by the composer for every pack, because
those are product behavior, not conversational style.

Why packs exist: live calls are hard-capped (default 5 minutes) and every
wasted exchange costs order completion. The generic script echoes items
one-by-one and settles pickup-vs-delivery LAST, which burns time on exactly
the calls that need it most. Each pack documents the time-rationale it
encodes.

BENCHMARK RULE (see docs/playbook/30-features/phone-orders/script-packs.md):
a pack's `status` may only move to "beat_baseline" after it outscores the
legacy control on the sim harness (scripts/phone_pack_bench.py) — mean judge
score not below baseline AND fewer mean caller turns. Packs that score below
baseline are marked "not_ready" and must not be recommended.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — import cycle guard, typing only
    from script_packs import PromptContext


def _upsell_guideline(ctx: "PromptContext", pack_default: str) -> str:
    """Merchant personality wins over the pack's upsell policy.

    'none' (merchant said never upsell) and 'active' (merchant wants two
    suggestions) override; otherwise the pack's own time-aware guideline
    applies.
    """
    if ctx.upsell_mode == "none":
        return "Do not upsell — never suggest additional items."
    if ctx.upsell_mode == "active":
        return (
            "Feel free to suggest add-ons that pair well (a drink, side, or "
            "dessert) — up to TWO natural suggestions per call, never pushy; "
            "move on as soon as they decline, and skip the suggestions "
            "entirely if the call is running long."
        )
    return pack_default


# Weak-spot extra hard rules (sim-harness failure modes: pay-now questions
# and group orders historically drag calls out / derail the close). Applied
# to every pack EXCEPT legacy (legacy is the untouched control).
_PAY_NOW_RULE = (
    "- If the caller asks to pay now or pay over the phone: payment happens "
    "through the secure text link right after the order is placed — say that "
    "in one sentence and keep the order moving. Never take card numbers on the call."
)
_GROUP_ORDER_RULE = (
    "- Group orders: keep each person's items together, confirm as you go, "
    "and read the final order back grouped by person — never re-ask about "
    "items already confirmed."
)


# ── pack definition shape ────────────────────────────────────────────

@dataclass(frozen=True)
class ScriptPackDef:
    id: str
    version: str
    label: str
    # One-line guidance for reps: which merchants this pack fits.
    recommend: str
    # control | pending | beat_baseline | not_ready — see BENCHMARK RULE above.
    status: str
    # Conversation guidelines: unordered principles the agent adapts to the
    # call (the composer bullets them under CONVERSATION GUIDELINES).
    guidelines: Callable[["PromptContext"], list[str]]
    # Extra HARD RULES lines appended after the shared non-negotiables.
    hard_rules: Callable[["PromptContext"], list[str]] = field(default=lambda ctx: [])


# ── efficient_v1: vertical-agnostic, time-optimized ──────────────────
#
# Rationale (5-minute cap): the generic script settles pickup/delivery after
# the whole order — so the delivery address surfaces at the worst moment —
# echoes items one-by-one, and always upsells. These guidelines steer the
# agent toward establishing order type early, confirming in small batches,
# a single compact read-back, and a conditional (skippable) upsell.

def _efficient_guidelines(ctx: "PromptContext") -> list[str]:
    return [
        f'Open with the greeting: "{ctx.greeting}" — then let the caller lead.',
        (
            f"Prefer establishing how they'd like the order ({ctx.order_types}) "
            "early in the call; it decides what information you'll need."
            + (
                " If it's delivery, get the address as soon as it comes up "
                "naturally rather than saving it for the end."
                if ctx.has_delivery else ""
            )
        ),
        (
            "Capture each item's name, size (when applicable), quantity, and "
            "modifications — but confirm in small batches every few items "
            "('Got it — two medium pepperonis and a Coke. Anything else?') "
            "rather than echoing every line back individually."
        ),
        _upsell_guideline(ctx, (
            "Offer at most ONE natural upsell, and only when the order still "
            "lacks a drink or side and the caller isn't rushed. If the order "
            "already includes a drink, the caller is brisk, or the call is "
            "running long — skip it."
        )),
        (
            "Pick up the caller's name wherever it fits naturally — it never "
            "needs to be its own interrogation step."
        ),
        (
            "Aim for one compact read-back at the end (items, sizes, "
            "modifications, total: size price + per-topping charge × toppings, "
            "then sides and drinks); between the batch confirms and that "
            "read-back, nothing should be confirmed twice."
        ),
    ]


def _efficient_hard_rules(ctx: "PromptContext") -> list[str]:
    return [_PAY_NOW_RULE, _GROUP_ORDER_RULE]


# ── pizzeria_v1: size + toppings grammar ─────────────────────────────
#
# Rationale: pizza orders live or die on the size→toppings exchange.
# Treating toppings as one-at-a-time "modifications" produces three
# round-trips per pizza. These guidelines steer toward size-first capture
# with toppings in the same exchange, and per-pizza (not per-topping)
# confirms.

def _pizzeria_guidelines(ctx: "PromptContext") -> list[str]:
    return [
        f'Open with the greeting: "{ctx.greeting}"',
        (
            f"Prefer settling how they'd like the order ({ctx.order_types}) early."
            + (
                " For delivery, get the address as soon as it comes up naturally."
                if ctx.has_delivery else ""
            )
        ),
        (
            "When a pizza comes up, lead with size and invite the toppings in "
            "the same exchange — 'What size, and what would you like on it?' "
            "beats three separate questions. Toppings on half the pizza go in "
            "modifications as 'half: <topping>'."
        ),
        (
            "Confirm each pizza as one unit ('one large pepperoni with "
            "mushrooms') rather than topping by topping; sides and drinks "
            "batch naturally into a single short confirm."
        ),
        _upsell_guideline(ctx, (
            "At most one natural pairing suggestion (garlic bread, drinks) — "
            "and only when the order has no side or drink and the caller is "
            "unhurried. Skip it for brisk callers or long calls."
        )),
        "Pick up the caller's name wherever it fits naturally.",
        (
            "Aim for one compact read-back at the end — each pizza with size "
            "and toppings, then sides and drinks, with the total (size price "
            "+ per-topping charge × number of toppings, then the rest)."
        ),
    ]


def _pizzeria_hard_rules(ctx: "PromptContext") -> list[str]:
    return [
        "- Specialty pizza we don't list → offer the closest listed pizza plus "
        "the toppings that get them there; quote the real per-topping price if asked.",
        _PAY_NOW_RULE,
        _GROUP_ORDER_RULE,
    ]


# ── cafe_quickserve_v1: counter-service speed ────────────────────────
#
# Rationale: cafe/quick-serve callers are usually on the move and orders are
# small. The name is useful EARLY (it goes on the order), pickup is the
# overwhelming default so the order-type check folds into the first
# exchange, and a drink's size + milk/mods land best as one question
# instead of three.

def _cafe_guidelines(ctx: "PromptContext") -> list[str]:
    return [
        f'Open with the greeting: "{ctx.greeting}"',
        (
            "Most calls are pickup — prefer folding the order-type check into "
            "the first exchange ('For pickup? And what can I get started?') "
            f"instead of making it its own step. Available: {ctx.order_types}."
            + (
                " For delivery, get the address as soon as it comes up."
                if ctx.has_delivery else ""
            )
        ),
        (
            "Get the caller's name early and naturally — it goes on the order "
            "— and only check spelling when it's genuinely unclear."
        ),
        (
            "For drinks, prefer capturing size and milk/modifications together "
            "('What size, and any milk preference?'). Confirm a few items at a "
            "time rather than echoing each one."
        ),
        _upsell_guideline(ctx, (
            "At most one light suggestion — a pastry with a drink-only order, "
            "or a drink with a food-only one — and only when the caller is "
            "unhurried. Skip it for brisk callers."
        )),
        (
            "Keep the pace quick and friendly — short questions, short "
            "confirms, one compact read-back with the total at the end."
        ),
    ]


def _cafe_hard_rules(ctx: "PromptContext") -> list[str]:
    return [_PAY_NOW_RULE, _GROUP_ORDER_RULE]


# ── indian_v1: multilingual-aware, courteous pacing ──────────────────
#
# Rationale: pairs with the Deepgram language=multi transcriber (Hindi/
# Punjabi + English code-switching). Spice level and bread/rice pairing are
# the two follow-ups every Indian-restaurant call needs — folding them into
# the same exchange as the dish saves a round-trip per item without rushing
# anyone. The read-back stays deliberately clear and unhurried: courteous
# pacing is part of the product here, so this pack banks its time savings
# in the capture phase, never the close.

def _indian_guidelines(ctx: "PromptContext") -> list[str]:
    return [
        f'Open warmly with the greeting: "{ctx.greeting}"',
        (
            f"Prefer settling how they'd like the order ({ctx.order_types}) "
            "early in the call."
            + (
                " For delivery, get the address as soon as it comes up naturally."
                if ctx.has_delivery else ""
            )
        ),
        (
            "Fold the natural follow-ups into the same exchange as the dish "
            "when it flows: spice level (mild, medium, or hot) for curry-style "
            "dishes, and whether they'd like naan or rice with it — one "
            "question, not three. Never assume a spice level the caller "
            "didn't give."
        ),
        (
            "Confirm a few items at a time in one short sentence rather than "
            "echoing each dish back."
        ),
        _upsell_guideline(ctx, (
            "One gentle suggestion at most — naan, rice, or a drink such as a "
            "lassi — and only when the order is missing it and the caller is "
            "unhurried. Never push; move on immediately if declined."
        )),
        (
            "Pick up the caller's name naturally; if it's unclear, politely "
            "ask them to spell it and confirm once."
        ),
        (
            "Keep the final read-back clear and unhurried — every dish with "
            "its spice level and sides, plus the total. Bank time in the "
            "capture, never by rushing the close."
        ),
    ]


def _indian_hard_rules(ctx: "PromptContext") -> list[str]:
    lines = []
    if ctx.multilingual:
        lines.append(
            "- Callers may switch between English and Hindi or Punjabi "
            "mid-sentence — follow the switch naturally and reply in the "
            "language the caller used most recently (English when unsure). "
            "Never comment on the switching."
        )
    lines += [
        "- Stay courteous and unhurried in tone even while keeping the call "
        "efficient — never cut the caller off mid-sentence.",
        _PAY_NOW_RULE,
        _GROUP_ORDER_RULE,
    ]
    return lines


# ── registry ─────────────────────────────────────────────────────────
# NOTE: "legacy" is intentionally NOT defined here. Legacy is the untouched
# generic prompt in src/api/routes/vapi_webhook.py — the control every pack
# is benchmarked against. script_packs.resolve_pack_id maps NULL/"legacy"/
# unknown ids to the legacy path, so this registry only carries real packs.

PACK_DEFS: dict[str, ScriptPackDef] = {
    p.id: p
    for p in (
        ScriptPackDef(
            id="efficient_v1",
            version="2",  # v2 = guidelines reframe (was prescriptive steps)
            label="Efficient (any business)",
            recommend=(
                "Any merchant on the 5-minute cap who wants faster calls "
                "without a vertical-specific flow."
            ),
            # 2026-07-17 v2 bench (guideline phrasing): mixed — beat control
            # on the pizzeria suite (9.29 vs 8.00) but scored below control on
            # its home generic suite (9.33 vs 9.67) and cafe (9.57 vs 9.71)
            # despite ~11-19% turn savings. NOT READY per the strict rule; do
            # not recommend until a revision beats its home suite.
            status="not_ready",
            guidelines=_efficient_guidelines,
            hard_rules=_efficient_hard_rules,
        ),
        ScriptPackDef(
            id="pizzeria_v1",
            version="2",
            label="Pizzeria",
            recommend=(
                "Pizza shops — size-first topping grammar, per-pizza confirms, "
                "half-and-half handling."
            ),
            # 2026-07-17 v2 bench (guideline phrasing): BEAT BASELINE —
            # 10.00 vs 8.00 score, 5.6 vs 6.7 turns, 100% completion on the
            # Tony's Pizza suite.
            status="beat_baseline",
            guidelines=_pizzeria_guidelines,
            hard_rules=_pizzeria_hard_rules,
        ),
        ScriptPackDef(
            id="cafe_quickserve_v1",
            version="2",
            label="Cafe / quick-serve",
            recommend=(
                "Cafes, coffee shops, counter-service — name early, pickup "
                "default, one-question drink capture."
            ),
            # 2026-07-17 v2 bench (guideline phrasing): BEAT BASELINE —
            # 9.86 vs 9.71 score, 4.7 vs 6.1 turns (fewest of any pack),
            # 100% completion on the Fern & Foam suite.
            status="beat_baseline",
            guidelines=_cafe_guidelines,
            hard_rules=_cafe_hard_rules,
        ),
        ScriptPackDef(
            id="indian_v1",
            version="2",
            label="Indian restaurant",
            recommend=(
                "Indian restaurants — pairs with the multilingual transcriber; "
                "spice/pairing capture in one exchange, courteous pacing."
            ),
            # 2026-07-17 v2 bench (guideline phrasing): BEAT BASELINE —
            # 9.43 vs 9.29 score, 5.6 vs 6.9 turns, 100% completion with
            # language=multi callers. Second consecutive run beating control
            # (v1 prescriptive phrasing also beat it).
            status="beat_baseline",
            guidelines=_indian_guidelines,
            hard_rules=_indian_hard_rules,
        ),
    )
}
