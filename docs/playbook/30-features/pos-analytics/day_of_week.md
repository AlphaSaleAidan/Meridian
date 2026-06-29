# Day Of Week

> Group: **pos-analytics**
> Tier: **Tier 3**
> Availability: **Base product (all merchants)**

## What it does

Best/worst days and day-specific revenue/traffic patterns.

## What it needs

Transactions with timestamps + 30 days of history.

## Example output

> Thursdays underperform by 18% vs Wednesday/Friday. Try a Thursday-specific promo — projected lift CA$520/mo.

## Where it lives

Source: `src/ai/agents/day_of_week.py` or `src/camera/day_of_week.py` (vision modules) or `src/ai/day_of_week.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
