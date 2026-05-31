# Discount Analyzer

> Group: **pos-analytics**
> Tier: **Tier 1**
> Plan: **Standard+**

## What it does

Which discounts actually drive incremental revenue vs. which just give margin away.

## What it needs

Transactions with discount fields (most POSes expose this).

## Example output

> Your '20% off Tuesdays' promo costs CA$420/mo in discount and lifts Tuesday revenue by CA$180/mo. Net: -CA$240. Kill it.

## Where it lives

Source: `src/ai/agents/discount_analyzer.py` or `src/camera/discount_analyzer.py` (vision modules) or `src/ai/discount_analyzer.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
