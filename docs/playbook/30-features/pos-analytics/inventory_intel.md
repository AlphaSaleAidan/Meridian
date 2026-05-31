# Inventory Intel

> Group: **pos-analytics**
> Tier: **Tier 2**
> Plan: **Standard+**

## What it does

Days-of-stock per SKU, reorder alerts, economic order quantity (EOQ) suggestions.

## What it needs

Transactions with SKUs + (ideally) supplier cost data.

## Example output

> Item #243: 3 days of stock left at current sell-through. Reorder by Friday or expect stockout by Tuesday.

## Where it lives

Source: `src/ai/agents/inventory_intel.py` or `src/camera/inventory_intel.py` (vision modules) or `src/ai/inventory_intel.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
