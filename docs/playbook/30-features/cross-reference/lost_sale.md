# Lost Sale

> Group: **cross-reference**
> Tier: **Tier 3**
> Availability: **Camera intelligence add-on**

## What it does

Walkaway patterns (entered → didn't transact) + estimates recoverable revenue.

## What it needs

Cameras at entrance + POS transactions.

## Example output

> 32 walkaways yesterday with >2 min dwell (interested but didn't buy). Estimated recoverable: CA$480 at your avg ticket.

## Where it lives

Source: `src/ai/agents/cross_ref/lost_sale_agent.py` or `src/camera/lost_sale.py` (vision modules) or `src/ai/lost_sale.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
