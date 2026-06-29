# Posture Purchase

> Group: **cross-reference**
> Tier: **Tier 4**
> Availability: **Camera intelligence add-on** (**FLAG [NEEDS AIDAN INPUT]:** skeletal tracking module may be a separate add-on; see `_open-questions.md` Q8)

## What it does

Correlates customer body posture/gesture patterns (browsing, hesitating, leaving) with purchase likelihood.

## What it needs

Cameras + POS + skeletal tracking module.

## Example output

> Customers who stop and turn (hesitation gesture) at the bakery case have 64% conversion. Staff approach within 30 sec lifts to 81%.

## Where it lives

Source: `src/ai/agents/cross_ref/posture_purchase_agent.py` or `src/camera/posture_purchase.py` (vision modules) or `src/ai/posture_purchase.py` (coordination)

---

_Last updated: 2026-06-29_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
