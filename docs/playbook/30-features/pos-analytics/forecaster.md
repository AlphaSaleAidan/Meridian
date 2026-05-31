# Forecaster

> Group: **pos-analytics**
> Tier: **Tier 5**
> Plan: **Standard+**

## What it does

7/30/90-day revenue forecasts with confidence intervals (AutoARIMA + LightGBM ensemble).

## What it needs

Transactions + 60+ days of history for tight intervals; 14+ days for rough forecasts.

## Example output

> Next 7 days projected revenue: CA$18,400 (CI: CA$16,800–CA$20,100). Above your trailing-30 average by 8%.

## Where it lives

Source: `src/ai/agents/forecaster.py` or `src/camera/forecaster.py` (vision modules) or `src/ai/forecaster.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
