# Propagate Flow — how digested data lands (Step C)

Scope: **propagate** (step 3 of connect → digest → propagate). How a `SyncResult`
(products, transactions, transaction_items, inventory) reaches the DB so the
dashboard sees it, and the invariants that keep it consistent.

## Write map

| Table | Conflict key | Written by |
|---|---|---|
| `products` | `org_id, external_id` | backfill, incremental, CSV, webhook |
| `transactions` | `org_id, external_id` | backfill, incremental, CSV, webhook |
| `transaction_items` | **`id, transaction_at`** (unified) | backfill, incremental, webhook |
| `categories` | `org_id, external_id` | webhook |
| `inventory_snapshots` | `org_id, product_id, location_id` | backfill, webhook |

Provider routing: writes to `transactions`/`transaction_items` pass through
`_route_by_provider` (src/db/supabase_rest.py) — the transient `provider` hint is
stripped, and when `POS_PER_PROVIDER_TABLES=1` rows go to `{provider}_{table}` so
ingestion paths can't overwrite each other. Flag OFF = base table, unchanged.

## Invariants (what keeps rows from clobbering / duplicating)

1. **Deterministic ids.** Every transaction + line-item id is `uuid5` of its
   natural key (`org_id`, `provider`, external id). Re-syncs upsert the SAME row
   (no duplicates, no PK churn, stable FKs); distinct rows never share an id.
2. **Unified `transaction_items` key.** All paths upsert on `(id, transaction_at)`.
   Previously the webhook path used `(org_id, external_id)` while backfill used
   `(id, transaction_at)` — that split could double-write a line item. Now one key.
3. **FK-safe order.** Backfill writes products → transactions → transaction_items,
   so line items never reference a not-yet-written transaction.
4. **Gate symmetry** (Step A). Connect opens both `businesses.pos_connected` and
   `organizations.pos_connection_status`; disconnect/teardown closes both. The
   dashboard gate can't be left half-open.

## Atomicity

The three table writes are still separate PostgREST upserts (REST can't span a
multi-table transaction without an RPC). With the deterministic-id work, a partial
failure is now **self-healing**: the connection is marked `status=error`, and the
next sync re-runs idempotently — the same rows upsert in place, so it converges
with no duplicates. The only residual gap is a transient window (a transaction
visible before its line items) until the retry.

**True single-statement atomicity** (all three tables in one transaction) requires
a Postgres RPC (`CREATE FUNCTION ... plpgsql`) — a schema migration. That's the
optional future hardening, deferred to the same coordinated migration that:
- promotes the `metadata.*` digest fields (`tenders`, `refund_cents`,
  `service_charge_cents`, `device_id`) to queryable top-level columns, and
- flips `POS_PER_PROVIDER_TABLES` on (phase-2 cutover).

Until then, idempotent retry is the consistency guarantee.

## Verification
`tests/api/test_pos_digest_flow.py`: deterministic/distinct ids (no dup, no
clobber, no cross-provider collision) and the unified `transaction_items` conflict
key. 30 tests passing across connect + digest.
