# Dwell Time

> Group: **pos-analytics**
> Tier: **Tier 2**
> Plan: **Premium+**

## What it does

Average dwell per zone, zone flow heatmaps, browse-to-buy funnel by area.

## What it needs

**Cameras required.** Zone polygons configured in dashboard.

## Example output

> Front display zone: avg 2:40 dwell. Customers who dwell >3 min have 40% higher average ticket. Move the impulse items closer.

## Where it lives

Source: `src/ai/agents/dwell_time.py` or `src/camera/dwell_time.py` (vision modules) or `src/ai/dwell_time.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
