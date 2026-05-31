# Peak Hours

> Group: **pos-analytics**
> Tier: **Tier 3**
> Plan: **Standard+**

## What it does

Revenue heatmap by hour-of-day + peak-hour optimization recommendations.

## What it needs

Transactions with timestamps (24 hours minimum data; 30 days for confidence).

## Example output

> Real peak is 12:15–12:45 PM (not 12:00 like you scheduled). Shifting staff +15 min projects +CA$340/mo.

## Where it lives

Source: `src/ai/agents/peak_hours.py` or `src/camera/peak_hours.py` (vision modules) or `src/ai/peak_hours.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
