# Product Velocity

> Group: **pos-analytics**
> Tier: **Tier 2**
> Plan: **Standard+**

## What it does

Per-SKU velocity ranking — rising stars, steady performers, dead stock.

## What it needs

Transactions with SKU/item identifiers + at least 30 days of history.

## Example output

> Top 5 rising: oat milk latte (+42% MoM). Dead stock: 7 SKUs with 0 sales in 30 days, CA$1,800 tied up.

## Where it lives

Source: `src/ai/agents/product_velocity.py` or `src/camera/product_velocity.py` (vision modules) or `src/ai/product_velocity.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
