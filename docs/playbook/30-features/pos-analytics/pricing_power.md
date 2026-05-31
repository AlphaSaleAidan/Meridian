# Pricing Power

> Group: **pos-analytics**
> Tier: **Tier 1**
> Plan: **Standard+**

## What it does

Price elasticity per item — which items you can raise without losing volume.

## What it needs

Transaction line items + at least 2 distinct historical prices per item.

## Example output

> Latte: low elasticity (-0.3). A 5% price increase projects +4.6% revenue with no volume hit. Estimated lift: CA$210/mo.

## Where it lives

Source: `src/ai/agents/pricing_power.py` or `src/camera/pricing_power.py` (vision modules) or `src/ai/pricing_power.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
