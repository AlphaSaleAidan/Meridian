# Staff Effect

> Group: **cross-reference**
> Tier: **Tier 3**
> Plan: **Premium+**

## What it does

Correlates staff presence in a zone with customer conversion and basket size.

## What it needs

Cameras detecting staff (uniform/badge) + POS.

## Example output

> When a staff member is in the wine zone, basket size +28%. Coverage gap Sat 3–5 PM — schedule staff in that zone.

## Where it lives

Source: `src/ai/agents/cross_ref/staff_effect_agent.py` or `src/camera/staff_effect.py` (vision modules) or `src/ai/staff_effect.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
