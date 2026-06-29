# Zone Conversion

> Group: **cross-reference**
> Tier: **Tier 3**
> Availability: **Camera intelligence add-on**

## What it does

Per-zone conversion rates and how each zone accelerates (or stalls) purchase.

## What it needs

Cameras + POS + zone polygons.

## Example output

> Bakery zone conversion: 38% (zone visits → purchase). Coffee zone: 78%. Customers who pass bakery then coffee convert at 91%. Don't break the path.

## Where it lives

Source: `src/ai/agents/cross_ref/zone_conversion_agent.py` or `src/camera/zone_conversion.py` (vision modules) or `src/ai/zone_conversion.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
