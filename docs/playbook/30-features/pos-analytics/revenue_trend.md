# Revenue Trend

> Group: **pos-analytics**
> Tier: **Tier 1**
> Availability: **Base product (all merchants)**

## What it does

Daily, weekly, and monthly revenue growth rates with trend-direction signals.

## What it needs

Transaction timestamps + totals. Works with any POS (live API or CSV).

## Example output

> Your weekly revenue is up 4.2% over the last 4 weeks; this week is on track to be 12% higher than last week.

## Where it lives

Source: `src/ai/agents/revenue_trend.py` or `src/camera/revenue_trend.py` (vision modules) or `src/ai/revenue_trend.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
