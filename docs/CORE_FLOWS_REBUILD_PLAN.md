# Core Flows — Understanding + Rebuild Plan (target: origin/main)

Goal: get the **basic function of the site** solid and understood — **connect POS →
digest read-only data → propagate it** — rebuilt fresh on `origin/main` (`f0507d3d`).
Old branches (`fix/canada-insights-currency` etc.) are **reference only**, not merged.
Don't touch main's visuals; functionality only. Nothing ships until these are done + understood.

Legend: ✅ verified directly in code · ⚠️ agent-reported, confirm before relying.

---

## 1. CONNECT POS — how it works on main today

Three entry paths, all landing in the `pos_connections` table:
- **Square OAuth**: `/api/square/authorize` → Square → `/api/square/callback` (`oauth.py`). HMAC-signed
  state (`OAUTH_STATE_SECRET`, 10-min TTL), token exchange, store `access_token_enc` +
  `refresh_token_enc` + `token_expires_at`, mirror gate, queue `run_backfill`.
- **Clover OAuth**: `/api/clover/authorize` → `/api/clover/callback` → `/api/clover/status`
  (`clover_oauth.py`). Same state scheme; stores `access_token_enc` AND
  `credentials_encrypted={access_token_enc, merchant_id}` (dual mirror); no refresh (tokens don't expire).
- **Manual/picker**: `POST /api/pos/test-connection` then `POST /api/pos/connect`
  (`pos_connections.py`) for toast/square/clover/generic; encrypts each cred, upserts connection,
  kicks the provider backfill.

**Correctness issues (rebuild targets):**
- ✅ `POST /api/pos/connect` body `org_id` is **not auth-guarded** (router guard only covers query/path;
  flagged "P1 follow-up" at `pos_connections.py:33`). Cross-tenant write risk.
- ✅ Token storage is **inconsistent**: OAuth uses `access_token_enc`(+`refresh_token_enc`), Clover/manual
  also fill `credentials_encrypted`; sync reads "whichever is populated." Two columns, drift-prone.
- ✅ `OAUTH_STATE_SECRET` falls back to an **ephemeral random secret** in dev → in-flight OAuth breaks on restart.
- ⚠️ Disconnect: Square token revoked, Clover is a no-op (by design — no revoke API). Org status cleared but `pos_system` retained.
- ⚠️ No double-connect idempotency / no multi-provider-same-org guard.

## 2. DIGEST read-only data — how it works on main today

Backfill (`src/{clover,square}/sync_engine.py`) → client fetch (`client.py`) → map (`mappers.py`) →
`SyncResult` (products/transactions/transaction_items/inventory). Clover: merchant=1 location, phases
merchant→employees→categories→items→orders(18mo, 30-day chunks)→item_stocks. Square: **multi-location**
(iterates locations), locations→team→catalog(item+variations)→orders→inventory.

**Correctness / read-completeness issues (rebuild targets):**
- ✅ **Clover webhook order KeyError is FIXED on main** (`webhook_handlers.py:187` uses `transaction_at`).
- ✅ **Clover incremental sync builds its mapper with an EMPTY `product_lookup`** (`sync_engine.py:~250`),
  while Square incremental loads it from DB. → line items likely get `product_id=NULL` on incremental. CONFIRM + fix.
- ⚠️ **Multi-tender/split payments**: both read only `tenders[0]`/`payments[0]` → 2nd tender's method &
  employee lost (~5–10% of food-service orders).
- ⚠️ **Clover multi-device**: `list_devices()` defined but never called → registers collapse into one location.
- ⚠️ **Square service charges** not extracted; **partial refunds** not tracked per-line (no `refund_cents`).
- ⚠️ Webhooks rely on cached product/employee lookups → stale on rename/new items (no lazy API fallback).

## 3. PROPAGATE — how it works on main today

Backfill/sync results written via **three separate `db.batch_upsert` calls** (products, transactions,
transaction_items). Connection state mirrored to **`organizations`** (`pos_system`,
`pos_connection_status`) and **`businesses`** (`pos_connected`); dashboard gate =
`businesses.pos_connected OR organizations.pos_connection_status=='connected'`. Webhooks call
`dashboard_cache.invalidate_org`; backfill triggers `MeridianPipeline.run_analysis_only`; staff seeded
via `_import_pos_staff` (idempotent). Note: main is mid-migration to **per-provider tables**
(`20260618_pos_per_provider_phase1/phase2`).

**Correctness issues (rebuild targets):**
- ⚠️ **Non-atomic writes**: 3 separate upserts, no rollback → a mid-failure leaves revenue without line items.
- ⚠️ **Inconsistent `transaction_items` conflict key**: backfill `id,transaction_at` vs webhooks
  `org_id,external_id` → duplication/inconsistent state when both touch the same item. CONFIRM.
- ⚠️ **Disconnect via webhook is incomplete**: only `pos_connections.status` set; `organizations` +
  `businesses` gate flags not reset → gate stays "open" after revoke.
- ✅ Gate state lives in **three places** (pos_connections + organizations + businesses) → drift.

---

## Rebuild plan (fresh on `feat/core-flows` off origin/main)

Build small, verify each on real/representative payloads, behavior-additive (don't break the green
connect handshake). Sequence matches the site's basic function:

**A. CONNECT (foundation)**
1. Single source of truth for the gate = `pos_connections.status`; stop relying on the 3-table mirror
   for reads (keep writes for back-compat during cutover). Make disconnect reset all of it via one helper.
2. Auth-guard body `org_id` on `/api/pos/connect` (+ test/disconnect/upload-csv) — validate against the caller's org.
3. Consolidate token storage to one convention; sync reads one place with a documented fallback.
4. Persistent `OAUTH_STATE_SECRET` everywhere (no ephemeral). (Pairs with the token reset.)

**B. DIGEST (read it all, correctly)**
5. Confirm + fix Clover incremental `product_lookup` (load from DB like Square).
6. Shared mapper base for Clover+Square; capture **all tenders** (JSONB array) not just `[0]`.
7. Square service charges + partial-refund capture (`refund_cents`); Clover device handling.
8. Webhook lazy-load for missing product/employee lookups; webhook event de-dup.
   *(Items 6–8 need a small migration — tenders/refund/service_charge/device columns.)*

**C. PROPAGATE (land it atomically)**
9. Atomic write of products+transactions+transaction_items (single RPC/transaction).
10. One consistent `transaction_items` conflict key everywhere.
11. Complete disconnect propagation (single helper used by both webhook + manual paths).

**Verify per step:** import + targeted tests, a real connect→backfill→dashboard round-trip on a preview
(cloudflared tunnel on the vite dev server proxying `/api` → local uvicorn) once the token reset settles.

**Open questions for prioritization:** which provider first (Square is more complete; Clover has the
incremental gap); do we adopt the in-progress per-provider tables or keep the shared tables for now.
