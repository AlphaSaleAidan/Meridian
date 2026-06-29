# Cashflow Forecast

> Group: **pos-analytics**
> Tier: **Tier 5**
> Availability: **Base product (all merchants)**

## What it does

30-day cash-flow projection with danger-zone detection (when cash might go negative).

## What it needs

Transactions + recurring expenses (where merchant has entered them) + processor settlement timing.

## Example output

> Cash position May 22: CA$2,400 (DANGER ZONE — below CA$3,000 buffer). Defer the supplier payment or push collections.

## Where it lives

Source: `src/ai/agents/cashflow_forecast.py` or `src/camera/cashflow_forecast.py` (vision modules) or `src/ai/cashflow_forecast.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
