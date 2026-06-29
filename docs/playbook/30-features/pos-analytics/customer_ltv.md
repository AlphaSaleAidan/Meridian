# Customer Ltv

> Group: **pos-analytics**
> Tier: **Tier 5**
> Availability: **Base product; richer with camera intelligence add-on (vision-based return-customer recognition)**

## What it does

Customer lifetime value prediction + churn risk per customer.

## What it needs

Customer IDs + 90+ days of transaction history.

## Example output

> 32 customers at high churn risk (no visit in 21+ days; usual cadence 7–10 days). Total LTV at risk: CA$4,800.

## Where it lives

Source: `src/ai/agents/customer_ltv.py` or `src/camera/customer_ltv.py` (vision modules) or `src/ai/customer_ltv.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
