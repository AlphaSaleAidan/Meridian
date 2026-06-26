# POS Connect — Session Progress (2026-06-16)

Branch: `session-2-canada-prep` (the **deployed** branch; pm2 `meridian-api` runs `/root/Meridian` on it).
Goal: business owners self-connect their POS (Square) from the customer portal, data propagates to the dashboard, unassisted.

## TL;DR — status

| Area | State |
|------|-------|
| Connect mechanism (both surfaces) | ✅ Fixed + live |
| Multi-worker OAuth state reliability | ✅ Fixed + live |
| Data propagation (read path) | ✅ Verified correct |
| Failure visibility | ✅ Surfaced (no more silent "connected, no data") |
| Frontend (picker panel → OAuth) | ✅ Deployed (`canada.meridian.tips`, SW `meridian-v7-20260616`) |
| Test harness | ✅ Green (4 layers) |
| Real end-to-end with a valid token | ⏳ Awaiting Aidan/Enoch reconnect via OAuth |

## Root causes found & fixed (in order)

1. **`OAUTH_STATE_SECRET` unset + `uvicorn --workers 4`** → each worker self-signed OAuth `state` with its own ephemeral secret → ~75% of callbacks `403 invalid state`. Fix: one shared `OAUTH_STATE_SECRET` in `/root/Meridian/.env` (gitignored; all workers load it via `load_dotenv`). Probe went 6/12 → 12/12.
2. **`organizations` insert missing NOT-NULL `vertical`** → org row never created → `pos_connections_org_id_fkey` FK violation. Fix (`oauth.py`, `clover_oauth.py`): add `"vertical": "other"`. (commit `0247568b`)
3. **`notifications` insert missing NOT-NULL `user_id`/`channel`/`scheduled_for`** → threw after the connection saved → "Connected but failed to save" + backfill skipped. Fix: queue backfill first, make the notification best-effort/non-fatal. (commit `67f18238`)
4. **Wrong handler** — the customer portal actually posts to **`POST /api/pos/connect`** (`pos_connections.py`), NOT the OAuth callback. That path: (a) inserted `pos_connections` without creating the `organizations` row → FK 409; (b) never set `businesses.pos_connected` (dashboard gate stayed locked); (c) Square got no backfill task. All fixed. (commit `af9e940f`)
5. **Silent backfill failure** — `run_backfill` had no error handling; a Square `401` (bad token) propagated out of the background task leaving `status=connected`/`last_error=null` ("connected, no data"). Fix: record `status=error`+`last_error` and revert the connected flags on failure; clear them on success. (commit `f0609688`)
6. **Picker panel pasted a manual Square token** (the 401 trap). Fix: `POSSelectorPanel` now uses 1-click OAuth (`/api/{square,clover}/authorize`) for Square/Clover; manual entry stays for non-OAuth POS (Toast). Return-path allowlist extended to `/canada/dashboard` + `/canada/setup`. (commits `4ccc21ec`, `74c50166` — **frontend deployed**)

Also: drill-down `get_day_transactions` filtered on `created_at` (row insert time) instead of `transaction_at` → backfilled historical days hidden. Fixed (`af9e940f`).

## The two connect surfaces (both now OAuth one-click)
- **Dashboard CTA**: `MerchantHomePage` "Connect your POS" → `/canada/merchant/onboard` (`MerchantOnboardingWizard.startSquareConnect` → `/api/square/authorize`). Was always OAuth.
- **Settings picker panel**: `POSSelectorPanel` → now redirects to `/api/square/authorize` (was manual token paste). Deployed this session.

Flow: `/api/{provider}/authorize` → provider login → `/api/{provider}/callback` (oauth.py) → org-ensure + `pos_connections` + `businesses.pos_connected=true` + `organizations.pos_connection_status='connected'` → `run_backfill` → `transactions`.

## Data propagation (verified correct)
`transactions` (filtered by `org_id` = `businesses.id`) → computed aggregates `daily_revenue`/`weekly_revenue`/`daily_product_performance` (sum sales, exclude voids) → `/api/dashboard/*` → portal. 60-day windows include backfilled history; pages auto-refetch when `pos_connected` flips. The post-backfill `MeridianPipeline` (insights/forecasts) is non-fatal.

Known limitation (by design, not built yet): **margins show ~100%** because the backfill writes no product cost. Direction from Aidan: build **inventory upload → cross-reference POS sales → true margin**. Until then, do not present a fake 100%.

## Test harness (`session-2-canada-prep`)
`scripts/run_connect_harness.sh` runs 4 layers, all green:
- `conformance` — `scripts/check_schema_conformance.py`: every connect-path insert's columns vs the live table `required` set (catches the NOT-NULL bug class).
- `inproc` — `tests/e2e/test_portal_connect.py`: real FastAPI callback via TestClient + FakeDB (now enforces NOT-NULL) + stubbed Square; asserts all dashboard-gating rows/flags.
- `ingestion` — `src/tests/test_pos_ingestion.py` (mock tier).
- `stateprobe` — `scripts/probe_oauth_state.py`: live multi-worker OAuth-state probe (fresh connection per request, or keep-alive masks the bug).

## Deploy / rollback
- Backend: changes take effect on `pm2 restart meridian-api`.
- Frontend: manual Contabo build. **No automatic SW versioning** — hand-bump `frontend/public/sw.js` `CACHE_NAME` each build. Build: `cd frontend && npm run build -- --outDir dist.new` (needs `frontend/.env.local`), verify, then `mv dist dist.bak-<ts> && mv dist.new dist`.
- This session's frontend rollback point: **`frontend/dist.bak-20260616-054423`**.

## Outstanding / next
- **Real end-to-end**: have Aidan/Enoch reconnect via the OAuth "Connect with Square" (valid token). Verify with `python scripts/verify_pos_connection.py <org_id> square`. Test orgs: Aidan `00cd98b5…` (stale pre-fix "connected/no-data" record — a reconnect resolves it), Enoch `51386ee4…` (no connection yet).
- **Margins feature**: inventory upload → cost cross-reference (not built).
- **Branch divergence**: `session-2-canada-prep` ↔ `origin/main` have diverged (~51 ↔ 64+ commits); today's fixes are only on session-2. Needs reconciliation.
- **Process note**: today's work (incl. a live frontend deploy) was done directly on the deployed branch with in-session review + a dist backup, not the usual branch→preview→PR flow.
