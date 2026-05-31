# Queue Monitor

> Group: **pos-analytics**
> Tier: **Tier 1**
> Plan: **Standard (estimated) / Premium (true camera-driven)**

## What it does

Real-time queue length and wait-time estimates with staffing-alert triggers.

## What it needs

Camera at checkout. POS-only fallback estimates from transaction-rate spikes.

## Example output

> Queue length at checkout: 6 people, ~3:20 estimated wait. Alert: staff up immediately.

## Where it lives

Source: `src/ai/agents/queue_monitor.py` or `src/camera/queue_monitor.py` (vision modules) or `src/ai/queue_monitor.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
