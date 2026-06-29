# Foot Traffic

> Group: **pos-analytics**
> Tier: **Tier 1**
> Availability: **Base product (estimated footfall) / Camera add-on (true camera-driven counts)**

## What it does

Hourly and daily footfall counts, entry-time patterns, conversion rate (visits ÷ transactions).

## What it needs

Cameras at entrance for true foot traffic. POS-only fallback estimates from transaction-time clustering.

## Example output

> Tue 12–1 PM: 84 visitors, 38 transactions, 45% conversion. Below your 58% average — investigate.

## Where it lives

Source: `src/ai/agents/foot_traffic.py` or `src/camera/foot_traffic.py` (vision modules) or `src/ai/foot_traffic.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
