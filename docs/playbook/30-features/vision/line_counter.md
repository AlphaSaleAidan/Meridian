# Line Counter

> Group: **vision**
> Tier: **pipeline**
> Availability: **Camera intelligence add-on**

## What it does

Counts directional crossings (in vs out) across virtual lines drawn on the camera view (typically at the entrance).

## What it needs

Detections from detector + line coordinates (set in dashboard).

## Example output

> Internal pipeline. Outputs in/out counts that feed foot_traffic (true entries vs exits).

## Where it lives

Source: `src/ai/agents/line_counter.py` or `src/camera/line_counter.py` (vision modules) or `src/ai/line_counter.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
