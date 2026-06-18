# POS Connection Flow — how it works + where every endpoint leads

Scope: **connect POS** (step 1 of connect → digest → propagate). Reflects the
hardened state on `feat/core-flows`. All connection state lives in the
`pos_connections` table; the dashboard "gate" lives in `businesses.pos_connected`
and `organizations.pos_connection_status`.

## The three ways a merchant connects

| Path | Providers | Entry file |
|---|---|---|
| OAuth | Square, Clover | `src/api/routes/oauth.py`, `src/api/routes/clover_oauth.py` |
| Manual / picker | Toast, Square, Clover, generic REST | `src/api/routes/pos_connections.py` |
| CSV upload | non-API systems | `src/api/routes/pos_connections.py` |

All three converge on the same `pos_connections` row + the same gate flags + the
same background backfill, then the dashboard reads the digested data.

## Endpoint map — where each one leads

### Square OAuth (`oauth.py`, prefix `/api/square`)
- `GET /api/square/authorize?org_id=&return_to=` → signs an HMAC state
  (`OAUTH_STATE_SECRET`, 10-min TTL) → **302 to Square's authorize page**.
- `GET /api/square/callback?code=&state=` → verify state → `OAuthManager.exchange_code`
  → upsert `pos_connections` (`access_token_enc`, `refresh_token_enc`,
  `token_expires_at`, `external_merchant_id`, `status=connected`) → open gate
  (`businesses.pos_connected=true`, `organizations.pos_system/pos_connection_status`)
  → queue `run_backfill` → **302 back to `return_to`**.

### Clover OAuth (`clover_oauth.py`, prefix `/api/clover`)
- `GET /api/clover/authorize?org_id=&return_to=` → 503 if `CLOVER_APP_ID/SECRET`
  unset (falls back to manual paste), else signs state → **302 to Clover**.
- `GET /api/clover/callback?code=&merchant_id=&state=` → verify state →
  `CloverOAuthManager.exchange_code` → upsert `pos_connections` with **dual token
  storage** (`access_token_enc` AND `credentials_encrypted={access_token_enc,
  merchant_id}`; Clover tokens don't expire) → open gate → queue
  `_run_clover_backfill` → **302 back**.
- `GET /api/clover/status?org_id=` → reads the connection → `{connected,
  merchant_id, status, last_sync_at, historical_import_complete, oauth_available}`.

### Manual / picker (`pos_connections.py`, prefix `/api/pos`, router dep `require_org_access`)
- `POST /api/pos/test-connection` `{pos_system, credentials}` → validate creds,
  no save. Square/Clover go through their env-aware clients
  (`_square_merchant_and_vertical` via `SquareClient`; `CloverOAuthManager.verify_token`).
  → `{success, message, details?}`.
- `POST /api/pos/connect` `{org_id, pos_system, credentials, restaurant_guid?}` →
  **requires JWT + org membership** (`require_org_member`, body-org tenancy guard)
  → encrypt creds → ensure `organizations` row (FK) → upsert `pos_connections`
  → open BOTH gate halves (`organizations.pos_connection_status=connected` +
  `businesses.pos_connected=true`) → queue provider backfill
  (`_run_toast_backfill` / `_run_clover_backfill` / `_run_generic_backfill`)
  → `{success, connection_id, syncing:true}`.
- `POST /api/pos/disconnect` `{org_id, pos_system}` → **requires JWT + org
  membership** → revoke Square token (Clover has no revoke) → `teardown_connection`:
  status=disconnected, **clear token**, `historical_import_complete=false`, and
  **close BOTH gate fields** → `{success, message}`.
- `POST /api/pos/sync/{org_id}/{pos_system}` → queue `_run_incremental_sync`
  (org_id in path → guarded by `require_org_access`).
- `GET /api/pos/connections/{org_id}` → list connections for the org.
- `POST /api/pos/upload-csv` → parse CSV → upsert transactions for non-API systems.

### Webhook disconnect (`webhooks.py`)
- Auth-revoked event → `_disconnect_merchant(connection_id)` → reuses
  `teardown_connection` (org_id resolved from the row) → same full gate teardown.

## The connection record (`pos_connections`)
`id, org_id, provider, status (connected|disconnected|error), external_merchant_id,
access_token_enc, refresh_token_enc (Square), token_expires_at (Square),
credentials_encrypted (JSONB; Clover + manual), historical_import_complete,
last_sync_at, last_error, created_at, updated_at`. Tokens encrypted via
`src/security/encryption.py` (AES-GCM). Conflict/lookup key: `(org_id, provider)`
(OAuth Square also matches on `external_merchant_id`).

## The dashboard gate (single rule, two mirrored fields)
`gate_open = businesses.pos_connected OR organizations.pos_connection_status == 'connected'`.
Connect opens **both**; disconnect/teardown closes **both** (and clears the token).
This symmetry is enforced — a half-open gate (the old disconnect bug) can't recur.

## Security / correctness invariants (Step-A hardened)
- **Tenancy:** `/connect` + `/disconnect` enforce JWT + org membership on the body
  `org_id` (closes the CA-1/CA-2 cross-tenant gap). Honors
  `TENANCY_ENFORCEMENT_DISABLED` rollback knob.
- **OAuth CSRF:** HMAC-signed state, 10-min TTL, shared `OAUTH_STATE_SECRET`;
  **production refuses to start without it** (both providers).
- **Env-aware Square:** test-connection + connect use `SquareClient`, honoring the
  configured environment (sandbox vs prod) and current `Square-Version` — no
  hardcoded prod URL.
- **Teardown:** disconnect clears the stored token and resets the import flag.

## Verification
`tests/api/test_pos_connect_flow.py` (15 tests, both providers): tenancy guard,
connect storage + gate open, disconnect teardown, OAuth state round-trip/tamper,
Square environment handling, no-hardcoded-prod-URL regression guard. A 12-min loop
re-runs it as a standing regression check.
