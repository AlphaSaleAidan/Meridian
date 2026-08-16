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
            "Feel free to suggest add-ons that pair well with what they've "
            "ordered — name a specific item from the MENU (a drink, side, or "
            "dessert), never a vague 'anything else?' — up to TWO natural "
            "suggestions per call, never pushy; move on as soon as they "
            "decline, and skip the suggestions entirely if the call is "
            "running long."
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
    # What the call IS. The original four packs all assume somebody is ringing
    # to buy food, and a lot of behaviour hangs off that — order types, menu
    # upsells, the read-back. Six of the ten trades take appointments instead
    # and one is a stock check, so the assumption has to be declared rather
    # than implied by a list of pack ids kept somewhere else.
    #   order       — buying items now (menu, order type, read-back)
    #   appointment — booking time (service, slot, length)
    #   enquiry     — a question, usually stock or hours
    # Conversation guidelines: unordered principles the agent adapts to the
    # call (the composer bullets them under CONVERSATION GUIDELINES).
    guidelines: Callable[["PromptContext"], list[str]]
    # Extra HARD RULES lines appended after the shared non-negotiables.
    hard_rules: Callable[["PromptContext"], list[str]] = field(default=lambda ctx: [])
    call_kind: str = "order"

    # ── What the trade actually sells, asks and pushes back on ──────────
    #
    # The three below are the difference between "a phone agent" and "a phone
    # agent that has worked in this trade". They are DATA, per pack, because
    # the right upsell for a nail salon (a fill while they are already in the
    # chair) has nothing in common with the right one for an auto shop (a
    # cabin filter while the car is already on the lift).

    # Concrete pairings. Never "would you like anything else" — a named thing,
    # tied to what they already asked for, offered once.
    upsells: Callable[["PromptContext"], list[str]] = field(default=lambda ctx: [])

    # (question, how to answer). The questions this trade's callers really
    # ask, in their words. Answering in one sentence and continuing is worth
    # more than any flourish elsewhere in the call.
    faqs: Callable[["PromptContext"], list[tuple[str, str]]] = field(default=lambda ctx: [])

    # (objection, the shortest handle that works). SHORTEST is the design
    # rule: a long rebuttal reads as pressure on a phone call, and pressure
    # loses the booking that a single honest sentence would have kept. One
    # attempt, then take the no gracefully — that is in the shared rules.
    objections: Callable[["PromptContext"], list[tuple[str, str]]] = field(default=lambda ctx: [])


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
            "Offer at most ONE natural upsell — name a specific drink, side, "
            "or dessert from the MENU that pairs with what they've ordered, "
            "never a vague 'anything else?' — and only when the order still "
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
            "At most one natural pairing suggestion, named from the MENU "
            "(e.g. the garlic bread or a drink) — and only when the order has "
            "no side or drink and the caller is unhurried. Skip it for brisk "
            "callers or long calls."
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
            "At most one light suggestion, named from the MENU — a pastry "
            "with a drink-only order, or a drink with a food-only one — and "
            "only when the caller is unhurried. Skip it for brisk callers."
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
            "One gentle suggestion at most, named from the MENU — a naan or "
            "rice to go with a curry, or a drink such as a lassi — and only "
            "when the order is missing it and the caller is unhurried. Never "
            "push; move on immediately if declined."
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


# ══ NICHE PACKS (2026-08-16) ══════════════════════════════════════════
#
# The four packs above are all ORDER-TAKING: somebody rings to buy food. Six
# of the ten trades Meridian now sells to do not take orders at all — they
# take APPOINTMENTS, and the call has a different shape. "What can I get you"
# is the wrong first question for a barbershop; "when suits you" is the wrong
# one for a pizzeria.
#
# Each pack below carries three things the generic prompt cannot know: what is
# genuinely worth offering in that trade, what its callers actually ring up
# and ask, and the shortest honest answer to the objection that loses the
# booking. The objection handles are deliberately ONE sentence. A phone call
# is not a landing page — a second attempt reads as pressure, and pressure
# loses the appointment that one straight answer would have kept.
#
# STATUS: every pack here ships "pending". None has been through
# scripts/phone_pack_bench.py yet, and the benchmark rule at the top of this
# file is not something to bend because the packs are new and look good.
# They are selectable and recommendable; they do not auto-apply.


def _appointment_guidelines(ctx: "PromptContext", *, unit: str, when_first: bool = True):
    """Shared spine for the trades that book time rather than sell items."""
    lines = [
        f'Open with the greeting: "{ctx.greeting}" — then let the caller lead.',
    ]
    if when_first:
        lines.append(
            "Find out WHAT they want and WHEN before anything else — those two "
            "decide everything that follows. Everything else can wait."
        )
    lines += [
        (
            f"Offer two or three specific {unit}s rather than asking when they are "
            "free — an open question makes the caller do the work and the call "
            "twice as long."
        ),
        (
            "Take the name and the mobile number once, wherever it fits — never "
            "as its own interrogation step."
        ),
        (
            "If they are a returning customer and you can see it, say so briefly. "
            "Being recognised is most of what a regular is paying for."
        ),
        (
            "Confirm back the service, the day, the time and roughly how long it "
            "takes, in one sentence. Length matters more than people expect — "
            "most complaints are about a slot running over, not the work."
        ),
    ]
    return lines


_APPOINTMENT_HARD_RULES = [
    "- Never invent availability. If you cannot see a free slot, say you will "
    "confirm by text rather than promising a time.",
    "- Never quote a price for work that has to be seen first — say what it "
    "usually starts at and that the final figure comes after a look.",
]


# ── barbershop_v1 ─────────────────────────────────────────────────────
def _barbershop_guidelines(ctx: "PromptContext") -> list[str]:
    return _appointment_guidelines(ctx, unit="time") + [
        "Ask who they usually see. A regular asking for their barber by name "
        "and being put with somebody else is the fastest way to lose them.",
    ]


PACK_DEFS.update({p.id: p for p in (
    ScriptPackDef(
        id="barbershop_v1",
        version="1",
        label="Barbershop & salon",
        recommend="Barbershops and salons — chair booking, regulars by name, retail on the shelf.",
        status="pending",
        call_kind="appointment",
        guidelines=_barbershop_guidelines,
        hard_rules=lambda ctx: _APPOINTMENT_HARD_RULES,
        upsells=lambda ctx: [
            "A beard trim alongside a cut — it is the same chair and the same visit.",
            "Booking the NEXT appointment before they hang up, if they come in regularly. "
            "Say roughly when they are due rather than asking an open question.",
            "The product they already use, if they mention their hair is dry or "
            "not holding — never a cold pitch at a stranger.",
        ],
        faqs=lambda ctx: [
            ("Do you take walk-ins?", "Answer honestly from the book — if today looks full, "
             "offer the first real slot instead of a maybe."),
            ("How much is a cut?", "Give the price plainly. Never hedge on a fixed-price service."),
            ("How long will it take?", "Give the honest length including the wait, not the best case."),
            ("Can I get in today?", "Check and answer with a specific time, or say the "
             "first opening is tomorrow at X."),
        ],
        objections=lambda ctx: [
            ("That's more than I usually pay", "Say what the price includes and leave it — "
             "never discount on the phone unless the shop has told you to."),
            ("I'll call back", "Offer to hold a slot for them for the day. Costs nothing "
             "and turns a maybe into a name in the book."),
            ("Is it going to be a long wait?", "Give the real number. A caller who is told "
             "twenty minutes and waits twenty minutes is not annoyed."),
        ],
    ),

    # ── nails_v1 ──────────────────────────────────────────────────────
    ScriptPackDef(
        id="nails_v1",
        version="1",
        label="Nail & lash studio",
        recommend="Nail and lash studios — service length varies hugely, so pin the service before the time.",
        status="pending",
        call_kind="appointment",
        guidelines=lambda ctx: _appointment_guidelines(ctx, unit="time") + [
            "Pin down WHICH service before offering a time. A fill and a full set "
            "are not the same appointment and cannot go in the same slot.",
            "Ask whether they are coming with anyone. Two people needing to be "
            "seen together changes which slots are actually possible.",
        ],
        hard_rules=lambda ctx: _APPOINTMENT_HARD_RULES,
        upsells=lambda ctx: [
            "Removal or a soak-off when they are coming from another set — it takes "
            "time you need to book, so it is a question you have to ask anyway.",
            "A pedicure alongside a manicure when the slot is long enough to allow it.",
            "Booking the fill before they leave — most people know roughly when they "
            "are due, so say the date rather than asking.",
        ],
        faqs=lambda ctx: [
            ("How long does a full set take?", "Give the honest length. Under-quoting a "
             "two-hour appointment is how the rest of the day slips."),
            ("Do you do removals?", "Answer, and say whether it adds time to the booking."),
            ("Can two of us come together?", "Check whether two technicians are free at "
             "the same time before saying yes."),
            ("How long will it last?", "Give a straight range and what shortens it."),
        ],
        objections=lambda ctx: [
            ("That's expensive", "Say what is included and how long it lasts. "
             "Per-week is how people actually judge it."),
            ("I need to check my schedule", "Offer to pencil a slot in and text them a "
             "confirmation they can cancel from."),
            ("Can I get in sooner?", "Offer the genuine first opening and the waiting list "
             "if there is one. Never invent an earlier slot."),
        ],
    ),

    # ── medspa_v1 ─────────────────────────────────────────────────────
    ScriptPackDef(
        id="medspa_v1",
        version="1",
        label="Med spa & aesthetics",
        recommend="Med spas — consultation-first, high ticket, and the one trade where over-promising is a real risk.",
        status="pending",
        call_kind="appointment",
        guidelines=lambda ctx: _appointment_guidelines(ctx, unit="time") + [
            "Route anything clinical to a consultation rather than answering it. "
            "A consultation is the product here — it is not a lesser outcome.",
            "Take the enquiry seriously and unhurriedly. These callers are spending "
            "several hundred and are usually nervous about asking.",
        ],
        hard_rules=lambda ctx: _APPOINTMENT_HARD_RULES + [
            "- NEVER give medical advice, promise a result, or say a treatment is "
            "safe or suitable for someone. Book the consultation instead — that is "
            "what it exists for.",
            "- Never discuss anyone else's treatment, results or attendance, even "
            "if the caller says they were referred by them.",
        ],
        upsells=lambda ctx: [
            "The consultation itself, when they ring asking about a treatment — it is "
            "free, it is the honest next step, and it books the room.",
            "A course or package ONLY if they raise cost first — never lead with it.",
            "Aftercare product at the end of a treatment booking, mentioned once.",
        ],
        faqs=lambda ctx: [
            ("How much is it?", "Give the starting price and say the exact figure comes "
             "from the consultation — never a firm quote for unseen work."),
            ("Does it hurt?", "Do not answer clinically. Say the practitioner covers "
             "exactly that in the consultation."),
            ("Is there downtime?", "Same — a consultation question, not a phone one."),
            ("Am I a good candidate?", "Never assess this. Book the consultation."),
        ],
        objections=lambda ctx: [
            ("I need to think about it", "Agree with them, and offer the free "
             "consultation as the no-commitment way to think about it properly."),
            ("It's a lot of money", "Say what is included and that the consultation "
             "confirms whether it is even the right treatment before anyone spends."),
            ("I had a bad experience elsewhere", "Acknowledge it in one sentence and "
             "offer the consultation. Do not compete with the other clinic."),
        ],
    ),

    # ── detailing_v1 ──────────────────────────────────────────────────
    ScriptPackDef(
        id="detailing_v1",
        version="1",
        label="Auto detailing",
        recommend="Detailing shops — package and vehicle size drive both the price and the bay time.",
        status="pending",
        call_kind="appointment",
        guidelines=lambda ctx: _appointment_guidelines(ctx, unit="slot") + [
            "Get the vehicle — make, and roughly the size. A three-row SUV and a "
            "hatchback are not the same job, the same price, or the same bay time.",
            "Ask what state it is in. Pet hair, smoke, or heavy sand is the "
            "difference between a two-hour job and a five-hour one.",
        ],
        hard_rules=lambda ctx: _APPOINTMENT_HARD_RULES,
        upsells=lambda ctx: [
            "The interior when they only asked for an exterior wash — it is the same "
            "visit and the same bay, and it is where the margin is.",
            "A coating or sealant if they mention keeping the car, not if they mention selling it.",
            "Pet hair or heavy soiling as an add-on — it has to be priced anyway, "
            "so raise it as a question rather than a surprise on collection.",
        ],
        faqs=lambda ctx: [
            ("How long will it take?", "Give the real bay time for that package and "
             "vehicle size, and say whether they can wait or should leave it."),
            ("How much for an SUV?", "Price by size — never quote the sedan price and "
             "correct it when the car arrives."),
            ("Do you do ceramic coating?", "Answer, and say it is a multi-day job "
             "with a cure time if it is."),
            ("Can I wait while it's done?", "Answer honestly — most full details are "
             "a drop-off, and saying so up front avoids a bad morning."),
        ],
        objections=lambda ctx: [
            ("That's more than a car wash", "One sentence on what is different, and "
             "leave it. They already know it costs more."),
            ("Can you do it cheaper?", "Offer the smaller package that genuinely costs "
             "less rather than discounting the big one."),
            ("I'll think about it", "Offer to hold a slot — the bay is the scarce thing, "
             "and saying so is honest rather than pushy."),
        ],
    ),

    # ── mobiledetailing_v1 ────────────────────────────────────────────
    ScriptPackDef(
        id="mobiledetailing_v1",
        version="1",
        label="Mobile detailing",
        recommend="Mobile detailers — the address and the access questions decide whether the job is even possible.",
        status="pending",
        call_kind="appointment",
        guidelines=lambda ctx: _appointment_guidelines(ctx, unit="window") + [
            "Get the ADDRESS early. It decides whether the job is possible at all "
            "and how much of the day it costs — it is not an afterthought.",
            "Ask about power and water at the location, and where the car will be "
            "parked. A van that arrives and cannot work has lost the whole slot.",
            "Offer a window rather than a time. Traffic is real and a missed exact "
            "time is remembered longer than a wide window.",
        ],
        hard_rules=lambda ctx: _APPOINTMENT_HARD_RULES + [
            "- Never book outside the service area. If the address is beyond it, say "
            "so straight away rather than taking the booking and cancelling later.",
        ],
        upsells=lambda ctx: [
            "A second vehicle at the same address — the drive is already paid for, "
            "so it is the best-value job of the day for both sides.",
            "Interior alongside exterior, since the van is already there.",
            "A recurring monthly visit if they mention keeping it clean — mobile "
            "customers are the ones who actually stick to it.",
        ],
        faqs=lambda ctx: [
            ("Do you come to me?", "Yes — confirm the address is inside the service "
             "area before going further."),
            ("Do you need my water?", "Answer plainly. Getting this wrong wastes a whole slot."),
            ("Where do you need to park?", "Say what access the van actually needs."),
            ("What if it rains?", "Say what the shop's policy is — do not invent one."),
        ],
        objections=lambda ctx: [
            ("It's cheaper at the car wash", "One sentence: they are not driving "
             "anywhere or waiting. Convenience is the product."),
            ("Can you come sooner?", "Offer the genuine first window. A route is a "
             "sequence — pretending otherwise makes somebody else late."),
            ("I'm not sure I'll be home", "Offer a window and ask whether the keys "
             "and the car will be accessible either way."),
        ],
    ),

    # ── autoshop_v1 ───────────────────────────────────────────────────
    ScriptPackDef(
        id="autoshop_v1",
        version="1",
        label="Auto repair",
        recommend="Repair shops — symptom first, never a diagnosis on the phone.",
        status="pending",
        call_kind="appointment",
        guidelines=lambda ctx: _appointment_guidelines(ctx, unit="slot") + [
            "Get the vehicle and the SYMPTOM in the caller's own words — what it is "
            "doing, when it started, whether it is drivable. Never translate it into "
            "a diagnosis.",
            "Say whether it is a wait-or-leave job. That is the single thing that "
            "decides how the customer plans their day.",
        ],
        hard_rules=lambda ctx: _APPOINTMENT_HARD_RULES + [
            "- NEVER diagnose a fault or quote a repair price on the phone. Book the "
            "look, give the diagnostic fee if there is one, and say the quote follows.",
            "- If they describe something unsafe — brakes, steering, smoke, a warning "
            "light they are still driving on — say plainly it should not be driven "
            "and offer the soonest slot.",
        ],
        upsells=lambda ctx: [
            "The service that is already due while the car is in — the labour "
            "overlaps and it saves them a second visit.",
            "Filters or wipers when the car is already on the lift, mentioned once "
            "with the price, never added silently.",
            "A courtesy check alongside the booked work, if the shop offers one free.",
        ],
        faqs=lambda ctx: [
            ("How much will it cost?", "Never quote unseen work. Give the diagnostic "
             "fee and say the quote comes before anything is done."),
            ("Can I wait for it?", "Give the honest bay time and say whether waiting "
             "is realistic."),
            ("Is it safe to drive?", "Do not assess it. If it sounds unsafe, say do "
             "not drive it and offer the soonest slot."),
            ("Do you need it all day?", "Answer honestly — a car kept longer than "
             "promised is the complaint shops actually get."),
        ],
        objections=lambda ctx: [
            ("The dealer quoted less", "Do not compete on the phone. Offer the look "
             "and say the quote comes with no obligation."),
            ("Why is there a diagnostic fee?", "One sentence: it is real time on the "
             "car, and say whether it comes off the repair."),
            ("I'll ring around", "Offer to hold a slot. If they book elsewhere they "
             "lose nothing, and the shop keeps its place in the day."),
        ],
    ),

    # ── smokeshop_v1 ──────────────────────────────────────────────────
    ScriptPackDef(
        id="smokeshop_v1",
        version="1",
        label="Smoke & vape shop",
        recommend="Smoke and vape shops — the call is almost always a stock check, and speed is the whole product.",
        status="pending",
        call_kind="enquiry",
        guidelines=lambda ctx: [
            f'Open with the greeting: "{ctx.greeting}" — then let the caller lead.',
            "Almost every call is 'do you have X'. Answer THAT first and fast. "
            "Anything else you need can come after.",
            "If it is in stock, offer to put it aside under their name. That is the "
            "whole job of this call — turning a question into a visit.",
            "If it is not in stock, say what is closest and when the item is back. "
            "Never leave a caller with only a no.",
            "Keep it short. These calls should be under a minute and a caller kept "
            "longer will simply ring the next shop.",
        ],
        hard_rules=lambda ctx: [
            "- Never confirm a customer's purchase history or preferences to anyone "
            "who rings asking about them.",
            "- Age-restricted goods: state the shop's ID requirement plainly if it "
            "comes up. Never suggest a way around it.",
        ],
        upsells=lambda ctx: [
            "The consumable that goes with what they asked for — coils with a device, "
            "papers with tobacco. One mention, at the point it is obviously relevant.",
            "The multi-buy if the shop has one and they are buying the single anyway.",
        ],
        faqs=lambda ctx: [
            ("Do you have X in stock?", "The whole call. Answer it first, plainly."),
            ("How much is it?", "Give the price. Never make somebody drive over to find out."),
            ("What time do you close?", "Answer immediately — this caller is deciding "
             "whether to set off right now."),
            ("Can you hold it for me?", "Say yes if the shop allows it and take a name."),
        ],
        objections=lambda ctx: [
            ("It's cheaper online", "One sentence: they have it today. Do not argue price."),
            ("Do you price match?", "Answer with the shop's actual policy. Never invent one."),
        ],
    ),

    # ── restaurant_v1 ─────────────────────────────────────────────────
    ScriptPackDef(
        id="restaurant_v1",
        version="1",
        label="Full-service restaurant",
        recommend="Full-service dining — the call is usually a table, not an order.",
        status="pending",
        call_kind="appointment",
        guidelines=lambda ctx: [
            f'Open with the greeting: "{ctx.greeting}" — then let the caller lead.',
            "Work out early whether this is a TABLE or an ORDER. They are different "
            "calls and guessing wrong wastes both people's time.",
            "For a table: party size and time first, then the name and mobile. "
            "Offer two or three specific times rather than asking when suits.",
            "Ask about the occasion only if they mention it. A birthday told to the "
            "kitchen is worth more than any upsell on this list.",
            "Take dietary requirements when they come up and read them back — this is "
            "the detail that ruins an evening when it is dropped.",
        ],
        hard_rules=lambda ctx: [
            "- Never confirm a table you cannot see availability for. Offer to text "
            "a confirmation instead.",
            "- Allergies are not preferences. Read them back and make sure they land "
            "in the booking notes.",
        ],
        upsells=lambda ctx: [
            "The set menu when the party is six or more — it is easier for the "
            "kitchen and usually better value, so it is an honest suggestion.",
            "A deposit-free pre-order for a large group, if the restaurant takes them.",
            "Mentioning the earlier sitting if the time they want is full — a "
            "specific alternative, not a vague 'we're busy'.",
        ],
        faqs=lambda ctx: [
            ("Do you take reservations?", "Answer, and take it there and then if so."),
            ("Do you have parking?", "One sentence. It decides whether they come."),
            ("Are you kid friendly?", "Answer plainly, including highchairs if asked."),
            ("Can you do gluten free / vegan?", "Answer honestly from the menu and "
             "note it on the booking — never guess on a dietary question."),
            ("How long do we get the table for?", "Give the real turn time up front. "
             "Discovering it on arrival is the complaint."),
        ],
        objections=lambda ctx: [
            ("That time doesn't work", "Offer the nearest two real alternatives "
             "immediately rather than asking what else suits."),
            ("You're fully booked?", "Offer the waiting list and the earlier or later "
             "sitting. Never leave them with just a no."),
            ("We might be late", "Say how long the table is held and offer to note it. "
             "Better than a no-show."),
        ],
    ),
)})
