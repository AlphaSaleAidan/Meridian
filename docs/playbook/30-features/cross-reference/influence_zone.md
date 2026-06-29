# Influence Zone

> Group: **cross-reference**
> Tier: **Tier 3**
> Availability: **Camera intelligence add-on**

## What it does

Identifies which store zones correlate with higher basket size when customers pass through them.

## What it needs

Cameras + POS, fused via journey tracker. Zones configured.

## Example output

> Customers who pass through the seasonal-display zone have 22% higher avg ticket. Move the high-margin item there.

## Where it lives

Source: `src/ai/agents/cross_ref/influence_zone_agent.py` or `src/camera/influence_zone.py` (vision modules) or `src/ai/influence_zone.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
