# Staffing

> Group: **pos-analytics**
> Tier: **Tier 4**
> Availability: **Base product (all merchants)**

## What it does

Optimal headcount per hour based on revenue, transaction rate, and labor-band targets.

## What it needs

Transactions + employee data + labor cost (where exposed).

## Example output

> Sat 11 AM–1 PM: scheduled 4, optimal is 5. Adding 1 staff projects +CA$180 revenue at +CA$45 labor cost = +CA$135 net.

## Where it lives

Source: `src/ai/agents/staffing.py` or `src/camera/staffing.py` (vision modules) or `src/ai/staffing.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
