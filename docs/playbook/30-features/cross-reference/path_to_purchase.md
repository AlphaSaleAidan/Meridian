# Path To Purchase

> Group: **cross-reference**
> Tier: **Tier 3**
> Availability: **Camera intelligence add-on**

## What it does

Maps the sequence of zones customers traverse before purchase vs walkaway.

## What it needs

Cameras across multiple zones + POS.

## Example output

> Purchasers hit: entrance → main display → checkout (avg 4 min). Walkaways hit: entrance → main display → back wall → exit (avg 6 min). Back wall is dead.

## Where it lives

Source: `src/ai/agents/cross_ref/path_to_purchase_agent.py` or `src/camera/path_to_purchase.py` (vision modules) or `src/ai/path_to_purchase.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
