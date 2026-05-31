# People Counter

> Group: **vision**
> Tier: **pipeline**
> Plan: **Premium+**

## What it does

Counts unique people based on tracker IDs over a time window (avoids double-counting the same person walking back and forth).

## What it needs

Detections from detector.

## Example output

> Internal pipeline. Outputs hourly/daily unique visitor counts.

## Where it lives

Source: `src/ai/agents/people_counter.py` or `src/camera/people_counter.py` (vision modules) or `src/ai/people_counter.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
