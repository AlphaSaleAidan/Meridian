# Promo Roi

> Group: **pos-analytics**
> Tier: **Tier 5**
> Plan: **Standard+**

## What it does

Promotion ROI calculator with diminishing-returns detection.

## What it needs

Transactions during + before/after promo windows.

## Example output

> Mother's Day promo: gross lift CA$1,200, discount cost CA$340, net ROI 2.5x. Diminishing returns triggered week 2 — pull it.

## Where it lives

Source: `src/ai/agents/promo_roi.py` or `src/camera/promo_roi.py` (vision modules) or `src/ai/promo_roi.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
