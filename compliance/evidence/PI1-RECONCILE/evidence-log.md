# Evidence — PI1-RECONCILE — processing integrity

**v0.1 — 2026-06-28.** This is the criterion that protects the product's core claim (computed financials).

## Type I evidence (real)
| Control | Location | Notes |
|---|---|---|
| Input validation (API) | Pydantic models, e.g. `src/api/routes/pos.py:12-20` | typed, pattern-constrained |
| Tolerant normalization | `src/services/pos_connectors/normalizer.py` | per-field error isolation; bad money → 0, not crash |
| Per-phase error capture | `src/services/pos_connectors/base.py:109-125`, `SyncResult.errors` | partial failures don't abort sync |
| **Reconciliation (Square)** | `src/services/reconcile.py` | compares ours vs Square truth, ±$1 tolerance, runs post-sync (`pos_connections.py:1048`), logs mismatch |

## Gaps
- Reconciliation is **Square-only**; Clover/Toast have no `_truth_cents()` equivalent (R-14).
- Mismatches are **log-only** (`reconcile.py:91`) — never surfaced to admin/merchant or alerted.
- Normalizer has **no negative-amount / duplicate-source-id guard** → manipulated/garbage feed corrupts
  analytics silently (R-13).
- `_ours_net_sales_cents()` prefers a materialized view — stale-view risk if refresh fails.

## Remediation
Extend reconciliation to Clover/Toast; persist results + alert on mismatch + surface on a dashboard; add
value/sign validation + idempotent upsert keyed on source transaction id.

## Status 🔴 awareness + Square reconciliation exist; coverage + surfacing are the gaps. PI1 is defensible to
defer to the next cycle if Aidan chooses the minimum-viable first report (see scope DECISION).
