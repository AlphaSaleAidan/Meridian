# Seasonality

> Group: **pos-analytics**
> Tier: **Tier 3**
> Availability: **Base product (all merchants)**

## What it does

Seasonal decomposition + calendar effects (holidays, weather, local events).

## What it needs

Transactions + 12+ months of history (or industry benchmark fallback if shorter).

## Example output

> June revenue typically +22% vs May. Prep inventory and staffing 2 weeks ahead.

## Where it lives

Source: `src/ai/agents/seasonality.py` or `src/camera/seasonality.py` (vision modules) or `src/ai/seasonality.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
