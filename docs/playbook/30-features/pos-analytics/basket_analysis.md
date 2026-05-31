# Basket Analysis

> Group: **pos-analytics**
> Tier: **Tier 2**
> Plan: **Standard+**

## What it does

Co-purchase pairs and bundle recommendations (Apriori-style market-basket).

## What it needs

Transactions with multi-item line items.

## Example output

> Customers who buy a latte buy a pastry 38% of the time. Bundling at CA$1 discount projects +CA$640/mo with 19% redemption.

## Where it lives

Source: `src/ai/agents/basket_analysis.py` or `src/camera/basket_analysis.py` (vision modules) or `src/ai/basket_analysis.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
