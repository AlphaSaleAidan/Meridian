# Cash Flow

> Group: **pos-analytics**
> Tier: **Tier 1**
> Availability: **Base product (all merchants)**

## What it does

14-day cash-position forecast incorporating processor fees, refunds, and tip-out timing.

## What it needs

Transactions + payment method + processor fee data (where exposed).

## Example output

> Projected cash position May 14: CA$8,400. Tightest day: May 7 (~CA$1,200) — consider deferring the supplier payment.

## Where it lives

Source: `src/ai/agents/cash_flow.py` or `src/camera/cash_flow.py` (vision modules) or `src/ai/cash_flow.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
