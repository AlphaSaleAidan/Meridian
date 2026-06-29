# Waste Shrinkage

> Group: **pos-analytics**
> Tier: **Tier 4**
> Availability: **Base product (all merchants)**

## What it does

Shrinkage rate, void/refund patterns, annual loss projection.

## What it needs

Transactions with void/refund fields. Big in smoke shops, restaurants with high-cost ingredients.

## Example output

> Void rate on shift 3-9 PM is 4.2% vs morning shift 1.8%. Investigate. Annualized: CA$8,400 in unexplained voids.

## Where it lives

Source: `src/ai/agents/waste_shrinkage.py` or `src/camera/waste_shrinkage.py` (vision modules) or `src/ai/waste_shrinkage.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
