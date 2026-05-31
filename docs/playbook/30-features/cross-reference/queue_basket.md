# Queue Basket

> Group: **cross-reference**
> Tier: **Tier 3**
> Plan: **Premium+**

## What it does

Correlates checkout queue wait time with basket size and abandonment rate.

## What it needs

Camera at checkout + POS.

## Example output

> Queue >3 min → abandonment rate 14% (vs 2% normal). Lost revenue: ~CA$220/day. Open the second register at queue=5.

## Where it lives

Source: `src/ai/agents/cross_ref/queue_basket_agent.py` or `src/camera/queue_basket.py` (vision modules) or `src/ai/queue_basket.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
