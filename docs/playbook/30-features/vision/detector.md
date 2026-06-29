# Detector

> Group: **vision**
> Tier: **pipeline**
> Availability: **Camera intelligence add-on**

## What it does

Per-frame person detection using YOLO11n + ByteTrack. Person-only (class 0). Confidence threshold 0.35. Assigns each detection to a configured zone polygon.

## What it needs

Live frames from rtsp_handler. Zone polygons (optional).

## Example output

> Internal pipeline. Outputs detection counts + zone assignments that feed foot_traffic, dwell_time, queue_monitor, and all cross-reference agents.

## Where it lives

Source: `src/ai/agents/detector.py` or `src/camera/detector.py` (vision modules) or `src/ai/detector.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
