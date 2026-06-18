"""
Canonical revenue arithmetic — the single source of truth for "how much money".

Every place that sums money MUST go through these helpers. The adversarial audit
found that staff scorecards, customer totals, day drill-downs, and the schedule
projected-revenue view each summed `total_cents` over *all* transactions with no
type filter — so voided/canceled orders inflated revenue, and refunds were never
netted. Centralizing the rule here prevents that class of bug from recurring.

Transaction `type` enum (set by the Square/Clover mappers): 'sale' | 'void'.
A voided/canceled/refunded order is mapped to 'void' and must NOT count as revenue.
`refund_cents` (when populated by a refund mapper) is subtracted from gross.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

# The only transaction type that represents realized revenue.
REVENUE_TYPES: frozenset[str] = frozenset({"sale"})


def is_revenue_txn(txn: Mapping) -> bool:
    """True if this transaction should count toward revenue (a completed sale,
    not a void/cancel/refund). Defaults to excluding anything not explicitly 'sale'."""
    return (txn.get("type") or "sale") in REVENUE_TYPES


def net_revenue_cents(txns: Iterable[Mapping]) -> int:
    """Net revenue in integer cents across `txns`:

        sum(total_cents for completed sales) - sum(refund_cents)

    Voids/cancels are excluded entirely; refunds are netted from gross. Returns an
    int (cents) — never floats — to avoid rounding drift. Use this instead of a
    raw `sum(t['total_cents'] for t in txns)` anywhere a revenue figure is shown.
    """
    gross = sum(int(t.get("total_cents") or 0) for t in txns if is_revenue_txn(t))
    refunds = sum(int(t.get("refund_cents") or 0) for t in txns if is_revenue_txn(t))
    return gross - refunds
