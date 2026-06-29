# Cross Reference Orchestrator

> Group: **coordination**
> Tier: **coord**
> Availability: **Camera intelligence add-on**

## What it does

Real-time fusion of camera events (detections) + POS events (transactions). Two modes: real-time (process_detections + process_transaction per event) and batch (analyze_batch over historical data). Coordinates PersonReIDService, JourneyTracker, and SkeletalTracker to build customer journeys, then runs the 10 cross-reference agents on fused data.

## What it needs

Cameras + POS connected.

## Example output

> Internal coordinator. Reps don't pitch this directly — it's the engine that lets us answer 'which zone correlates with higher tickets' in near-real-time.

## Where it lives

Source: `src/ai/agents/cross_reference_orchestrator.py` or `src/camera/cross_reference_orchestrator.py` (vision modules) or `src/ai/cross_reference_orchestrator.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
