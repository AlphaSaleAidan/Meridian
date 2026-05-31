# Return Customer

> Group: **cross-reference**
> Tier: **Tier 3**
> Plan: **Premium+**

## What it does

Compares returning vs first-time customer journeys and spend patterns (using anonymous person re-ID).

## What it needs

Cameras + POS + person re-ID service (face-anonymous, body-feature-based).

## Example output

> Returning customers spend 1.8x more than first-timers but only browse 60% of the store. Layout favors discovery — good for first-timers, less for regulars.

## Where it lives

Source: `src/ai/agents/cross_ref/return_customer_agent.py` or `src/camera/return_customer.py` (vision modules) or `src/ai/return_customer.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
