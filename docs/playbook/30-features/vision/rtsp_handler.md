# Rtsp Handler

> Group: **vision**
> Tier: **pipeline**
> Plan: **Premium+**

## What it does

Connects to a camera's RTSP/RTSPS stream and maintains a small frame buffer (drops stale frames to keep the freshest).

## What it needs

Supported camera with RTSP or RTSPS exposed. See 20-camera-integrations/.

## Example output

> Internal pipeline. Reps don't pitch this directly — it's the plumbing that makes camera intelligence work.

## Where it lives

Source: `src/ai/agents/rtsp_handler.py` or `src/camera/rtsp_handler.py` (vision modules) or `src/ai/rtsp_handler.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
