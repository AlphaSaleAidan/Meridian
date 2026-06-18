# Deploy Runbook — core-flows (code + coordinated migration, together)

Ships PR #118 (`feat/core-flows`) **with** the DB-side changes as one coordinated
operation, so the deterministic-id transition lands cleanly. Backend auto-deploys
from `main` via Railway. Frontend is untouched (no step needed).

> Execution requires prod access (Supabase migration apply + merge to `main` +
> trigger re-backfill). These are gated for the agent by design — run this
> yourself or explicitly grant access. Do a DB snapshot first.

## Why a re-backfill (the id-reconciliation)
The new code uses deterministic `uuid5` ids. Existing rows have random ids, and
existing line items never stored their source line-id, so the deterministic id
**cannot be recomputed in place** — a pure-SQL id rewrite is impossible for
`transaction_items`. The clean reconciliation is to **clear POS-derived rows and
re-backfill**: the new code regenerates deterministic ids (and the newly-captured
tenders/refunds/service-charges/device) from source. Without this, the first
post-deploy sync orphans old line items alongside new ones (transient
double-counting).

## Order of operations (one window)
1. **Snapshot** the DB (Supabase backup / `pg_dump` of `transactions`,
   `transaction_items`, `products`, `pos_connections`).
2. **Apply migrations**, in this order:
   1. `20260619_pos_metadata_to_columns.sql` (generated columns from metadata)
   2. `20260618_pos_per_provider_phase1.sql` (additive provider tables — copies the
      new generated columns via `LIKE … INCLUDING ALL`)
   3. `20260618_pos_atomic_write_rpc.sql` (the `pos_sync_upsert` function)
   4. `20260618_pos_per_provider_phase2_cutover.sql` **only if** flipping
      per-provider on now (writes rewire + UNION view) — otherwise defer.
   - Validate each against the live schema first (each file has a ⚠️ header).
3. **Merge PR #118 → `main`** → Railway deploys the backend.
4. **Set env vars** in Railway (verify, don't assume):
   - `CLOVER_ENVIRONMENT=production`, `CLOVER_REGION=na` (US+Canada)
   - `OAUTH_STATE_SECRET` present (prod refuses to start without it)
   - Leave `POS_ATOMIC_WRITE` and `POS_PER_PROVIDER_TABLES` **off** unless steps
     2.3/2.4 were applied and validated; flip them only then.
5. **Re-backfill each connected org** (the id-reconciliation):
   - For each `pos_connections` row with `status='connected'`: delete its
     `transaction_items` then `transactions` (FK order), then
     `POST /api/pos/sync/{org_id}/{pos_system}` (or re-run the backfill).
   - Idempotent from here on — deterministic ids mean subsequent syncs upsert in place.
6. **Verify**:
   - `GET /health` → 200; `GET /api/clover/status?org_id=…` sane.
   - No duplicate line items: `select transaction_id, count(*) … group by … having count(*) > expected`.
   - Spot-check a refunded order → `refund_cents` populated; a split-payment order
     → `tenders` has >1 entry; dashboard revenue numbers sane.
   - Re-run the connect monitor → ✅.

## Rollback
- Revert the `main` merge (Railway redeploys previous) and restore the snapshot.
- Generated columns + provider tables are additive; dropping them is safe if needed.
- `POS_ATOMIC_WRITE` / `POS_PER_PROVIDER_TABLES` off = pre-change behavior.

## What ships
Connect hardening, digest captures (tenders/refunds/service-charges/device/
incremental product links), deterministic ids + unified conflict key, Clover
regions, atomic-write path (flag-gated), metadata→columns. 35 tests green on the branch.
