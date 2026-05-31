# Pipeline

> Group: **vision**
> Tier: **pipeline**
> Plan: **Premium+**

## What it does

Top-level orchestration of the vision system: rtsp_handler → detector → counters → supabase_writer.

## What it needs

All vision modules + Supabase writer for persistence.

## Example output

> Internal pipeline. One pipeline instance per camera. Runs continuously while camera is connected.

## Where it lives

Source: `src/ai/agents/pipeline.py` or `src/camera/pipeline.py` (vision modules) or `src/ai/pipeline.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
