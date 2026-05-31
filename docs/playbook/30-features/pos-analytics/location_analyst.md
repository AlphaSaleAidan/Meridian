# Location Analyst

> Group: **pos-analytics**
> Tier: **Tier 3**
> Plan: **Command**

## What it does

Multi-location comparison, best-practice transfer (what location A does that B doesn't), underperformance flags.

## What it needs

2+ locations connected (Command plan only).

## Example output

> Location B's lunch revenue is 32% below Location A. A runs a CA$8 lunch combo; B doesn't. Transfer the combo to B.

## Where it lives

Source: `src/ai/agents/location_analyst.py` or `src/camera/location_analyst.py` (vision modules) or `src/ai/location_analyst.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
