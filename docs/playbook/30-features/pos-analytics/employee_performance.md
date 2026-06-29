# Employee Performance

> Group: **pos-analytics**
> Tier: **Tier 4**
> Availability: **Base product; richer with camera intelligence add-on (camera-detected staff zones via staff_effect)**

## What it does

Per-employee revenue, upsell rate, tip-out fairness, void patterns.

## What it needs

Employee IDs on transactions (Square, Toast, Clover, Treez expose this well; varies by POS).

## Example output

> Jenna's upsell rate is 38% vs team avg 22%. Mike's voids are 2x team avg — coach or audit.

## Where it lives

Source: `src/ai/agents/employee_performance.py` or `src/camera/employee_performance.py` (vision modules) or `src/ai/employee_performance.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
