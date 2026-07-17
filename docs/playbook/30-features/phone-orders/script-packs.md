# Phone Agent Script Packs — Per-Vertical Conversation Guidelines

> Status: **LIVE, opt-in** (flag-gated: every merchant runs the Standard script until they explicitly pick a pack)
> Why this exists: calls are hard-capped (5 minutes by default) and **every wasted
> exchange costs order completion**. The Standard script confirms items one-by-one
> and asks pickup-vs-delivery *last* — packs steer the agent to spend those
> seconds on the order instead.
>
> **A pack is a set of guidelines the agent adapts, not a script it recites.**
> Packs describe principles and priorities — "prefer establishing pickup vs
> delivery early", "confirm items in small batches rather than echoing every
> line", "at most one natural upsell, only when the order lacks a drink/side" —
> and the agent follows the caller's lead within them. The non-negotiables
> (read-back + confirmation before submit, the pay-link line, delivery-address /
> off-menu / pay-now handling) are HARD RULES rendered identically for every
> pack, because those are product behavior, not conversational style.

## The one rule that matters

**A pack may only be recommended after it beats the Standard script on the sim
harness.** Run `scripts/phone_pack_bench.py` (needs `DEEPSEEK_API_KEY`): a pack is
default-eligible only when its mean judge score is **not below** the Standard
control **and** it uses **fewer caller turns**. Packs that miss that bar are marked
*(beta)* in the wizard and `not_ready`/`pending` in the registry — merchants can
still opt in, but reps must not pitch them. No exceptions: past prompt "improvements"
have scored *worse* than baseline on this harness, which is why the baseline is
sacred and the default never changes.

## How it works

- `phone_agent_config.script_pack` selects the pack. `NULL` / empty / `legacy` /
  any unknown value → the **exact current generic prompt, byte-for-byte** (golden
  snapshot tests in `tests/api/test_script_packs.py` prove it). Any error in the
  pack layer also falls back to Standard — a live call can never be stranded by a pack.
- `business_type` is stored alongside it but **never auto-selects a pack** — it only
  drives the "Suggested for your business type" hint in the wizard.
- Packs change the CONVERSATION GUIDELINES only. The HARD RULES block (read-back +
  confirmation before submit_order, pay-link line, safety protections) and every
  merchant feature — personality, reservations, transfer-to-human, menu link,
  sold-out handling, the call-cap pacing line — render identically in every pack.
- Composition lives in `services/phone_agent/script_packs.py` (+ `script_pack_defs.py`);
  selection UI is in the phone setup wizard (Voice step); migration
  `supabase/migrations/20260717_phone_script_pack.sql`.

## The packs (v2 guideline phrasing — bench of 2026-07-17, scripts/phone_pack_bench.py)

| Pack | For | Score vs Standard (home suite) | Turns vs Standard | Status |
|------|-----|-------------------------------:|------------------:|--------|
| `legacy` — Standard | everyone (default) | — | — | control |
| `efficient_v1` | any business on the call cap | 9.33 vs 9.67 (generic) · beat on pizzeria (9.29 vs 8.00) · 9.57 vs 9.71 (cafe) | 5.3–5.5 vs 5.4–6.7 | **not ready** — below control on its home suite; do not recommend |
| `pizzeria_v1` | pizza shops (size-first topping grammar) | **10.00 vs 8.00** | **5.6 vs 6.7** | **beat baseline** — recommendable |
| `cafe_quickserve_v1` | cafes / counter service (name early, one-question drink capture) | **9.86 vs 9.71** | **4.7 vs 6.1 (fewest of any pack)** | **beat baseline** — recommendable |
| `indian_v1` | Indian restaurants (pairs with the multilingual transcriber) | **9.43 vs 9.29** | **5.6 vs 6.9** | **beat baseline** — recommendable (second consecutive winning run) |

All runs: fixed scenario sets including the historical weak spots (group order,
pay-now question) plus a rambling-caller time-pressure scenario; identical menus,
greeting, and cap for control and pack; judge menu = the exact MENU block in the
prompt; 100% completion everywhere. Verdicts are **within-run** (control and pack
face identical scenarios in the same run) — absolute scores drift between runs, so
never compare a pack's score to a control from a different run. Full transcripts
and per-suite tables land in the bench `--out` directory.

Note: the v2 guideline phrasing outperformed the v1 prescriptive step-by-step
phrasing — pizzeria and cafe flipped from not-ready to beating baseline once the
same content was expressed as adaptable principles instead of a rigid flow.

## What reps should say

- A pack is **a set of guidelines the agent adapts, not a script it recites** —
  the agent still follows the caller's lead; the pack just changes what it
  prioritizes.
- **Pizzerias, cafes/quick-serve, Indian restaurants**: recommend the matching
  pack — all three beat Standard on the harness (better or equal accuracy, fewer
  exchanges per call).
- **Everyone else**: leave it on *Standard (current)*. The *(beta)* Efficient
  script is opt-in only — it saves turns but hasn't beaten Standard on its own
  suite yet; never present it as the default.
- Changing the script never touches pricing, payment, transfer, or menu behavior —
  the read-back-and-confirm-before-submit and pay-link steps are hard rules in
  every pack.

## Shipping a new pack (or revising a not-ready one)

1. Add/modify the pack in `services/phone_agent/script_pack_defs.py` with
   `status="pending"` and the rationale in comments.
2. Add its suite (menu + scenarios) to `scripts/phone_pack_bench.py` if it's a new
   vertical.
3. Run the bench. Paste the table into the PR. Score ≥ control **and** fewer turns →
   `beat_baseline`; score below control → `not_ready` (say so in the pack's comment).
4. Only `beat_baseline` packs get a wizard suggestion or a rep recommendation.
   The Standard default is never changed by a pack shipping.
