# Action Prioritizer

> Group: **pos-analytics**
> Tier: **Tier 5**
> Plan: **Standard+**

## What it does

Ranks every agent recommendation by ROI ÷ effort into the daily Top 3 actions.

## What it needs

Outputs from tier 1–4 agents.

## Example output

> Today's Top 3: (1) Pull the Tuesday discount [CA$240/mo, 5 min], (2) Reorder SKU #243 [stockout in 3 days], (3) Staff +1 Sat lunch [+CA$135 net].

## Where it lives

Source: `src/ai/agents/action_prioritizer.py` or `src/camera/action_prioritizer.py` (vision modules) or `src/ai/action_prioritizer.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
