# POS Ingestion Audit — 2026-06-03

Discovery-only audit. No new features, no schema changes, no prod
writes. The deliverable is this document.

Context: the Wave-1 and Phase-1 work established that the production
Meridian DB holds 3 transactions and no customer-identity column at
all (`eval/reports/recon_2026-06-03.md`). Before building new ingestion
plumbing, we want to know what already exists, what works, what's
stubbed, and what's missing. Reps will operate connections individually
per location (concierge, not merchant self-serve); the beta is
Canada/CAD on `/canada/*`; primary targets are Square and Clover.

The codebase already has substantial POS work: a 4,740-line frontend
provider registry, a 1,316-line backend system-config registry covering
80 POS systems, two FastAPI routers for connection management, two
front-end picker components, two onboarding wizards (US + Canada),
encrypted token storage, sync engines for Square / Toast / Clover, and
a canonical normalization layer with automotive + cannabis extensions.
The question this doc answers is: **of that, what's actually wired
end-to-end, and what stops a rep from connecting a real Canadian
Square or Clover merchant today?**

Status legend:
- **WORKING** — implemented end-to-end and operational
- **PARTIAL** — implemented but a real call path drops or breaks
- **STUB-UI-ONLY** — UI exists but does not call a backend
- **MISSING** — referenced in code or docs but not actually present

---

## 1. Connection UI

### Frontend provider registry — `frontend/src/data/pos-systems.ts` (4,740 lines)

**WORKING.** Single source of truth on the front end. 80 POS systems
keyed by `posKey`, each with rich metadata: `status`
(`integrated | coming_soon | contingency | unsupported`), `tier` (1–5),
`integrationStatus` (apiAvailable / oauthSupported / webhooksSupported
/ sandboxAvailable / estimatedIntegrationEffort), `contingencyPlan`,
`connectionRequirements` (required credentials + permissions +
step-by-step instructions), vertical tags, and per-provider
`dataAvailable` flags. Square (key=`square`), Clover (key=`clover`),
Toast, Lightspeed (×2), Shopify, Boulevard, Mindbody, Greenline (the
Canadian cannabis option), Heartland's three branches, plus a long
tail. Bank-channel rebrands (`pnc-pos`, `wells-fargo-pos`, …) appear
as separate Clover-aliased entries on both sides (frontend list +
backend `SYSTEM_ALIASES`). The data is comprehensive and current.

### POSSelectorPanel — `frontend/src/components/POSSelectorPanel.tsx` (633 lines)

**WORKING.** Searchable picker used by `SettingsPage`. Renders the
80-system catalogue with status badges. Surfaces two layouts (A/B) for
the selected provider — both wired to `/api/pos/test-connection` and
`/api/pos/connect`. Supports the waitlist call for non-integrated
systems. Currency-aware theming (CAD/USD palettes).

### POSSystemPicker — `frontend/src/components/POSSystemPicker.tsx` (715 lines)

**WORKING.** Distinct from POSSelectorPanel. Used by the Canada wizard
and the Canada portal's lead-detail page. Takes
`portalContext: 'us' | 'canada'`, `currency: 'USD' | 'CAD'`, and an
optional `vertical` slug; surfaces matching systems first inside each
status group. Calls `/api/pos/select` for bookkeeping; the actual
credential collection is delegated to the wizard step that owns the
picker.

### CustomerOnboardingWizard — `frontend/src/pages/customer/CustomerOnboardingWizard.tsx` (1,144 lines)

**PARTIAL.** US/merchant self-serve wizard. The connect step lists
three providers inline (`square`, `clover`, `toast`), each with field
definitions:

```
square  → fields: [access_token]
clover  → fields: [api_key, merchant_id]
toast   → fields: [api_key, restaurant_guid]
```

Calls `connectPos(provider, apiKey)` from `useAuth()`. **Two breakage
points downstream** (see §2): the wizard collects multi-field
credentials for Clover and Toast but `connectPos` only forwards a
single `access_token` field, so the backend test step rejects
Clover/Toast with "Access token and Merchant ID required" /
"All three fields are required". Square is the only provider that
works end-to-end through this wizard today.

### CanadaCustomerOnboardingWizard — `frontend/src/pages/canada/portal/CanadaCustomerOnboardingWizard.tsx` (1,156 lines)

**PARTIAL.** Canadian wizard the reps actually use. Passes
`currency="CAD"` to `POSSystemPicker` and uses CAD pricing
(`CAD_RATE` import, `monthly_price_cad_cents`). The POS step calls
`/api/pos/select` (POST `{org_id, pos_system, connection_status}`) —
**this records a selection but does NOT initiate any token exchange or
data pull.** Connection-status semantics is bookkeeping only. No call
path from this wizard reaches `/api/pos/test-connection`,
`/api/pos/connect`, `/api/square/authorize`, or any sync trigger.

### CanadaPortalAccountsPage — `frontend/src/pages/canada/portal/CanadaPortalAccountsPage.tsx`

**STUB-UI-ONLY (the operational pieces).**
- Per-client tile shows `client.pos_provider` — read from
  `deriveClientsFromLeads(deals)` which derives clients from the
  `canada_leads` table, **not** from `pos_connections`. So the UI
  surfaces the lead's recorded selection, not actual connection state.
- "Last POS sync" timestamp is hard-coded: `new Date(Date.now() - 1000 * 60 * 47)` (always "47 minutes ago").
- "Sync POS Data" button handler: `setSyncingId(client.id); setTimeout(() => setSyncingId(null), 2000)` — pure UI animation, no fetch.

So the Canada portal's "active POS connection" view is decorative.

---

## 2. OAuth / auth flow

### Square — backend `src/api/routes/oauth.py`

**WORKING (backend).** Full OAuth flow implementation:
- `GET /api/square/authorize?org_id=…` — HMAC-signed state token
  (`OAUTH_STATE_SECRET` env, 10-min TTL), redirects to Square's
  authorize URL.
- `GET /api/square/callback?code=…&state=…` — verifies HMAC state,
  exchanges code for tokens via `OAuthManager.exchange_code`, encrypts
  with `encrypt_token`, upserts into `pos_connections`, creates a
  notification, kicks off `workers.backfill.run_backfill` as a
  background task, redirects to `/app/settings?oauth=success`.
- `GET /api/square/status` — connection status by `org_id`.
- Refusal-to-start guard in prod: if `OAUTH_STATE_SECRET` is unset and
  `RAILWAY_ENVIRONMENT`/`RENDER` is set, the import raises (preventing
  silent insecure boot).

The backend is production-grade. Mounted in `app.py`:
`app.include_router(oauth_router)`.

### Square — frontend trigger

**MISSING.** No frontend code anywhere (`/root/Meridian/frontend/src`)
calls `/api/square/authorize`, redirects to it, or generates a
"Connect with Square" button that opens the OAuth URL. Searched:
`Connect Square`, `/api/square/authorize`, `squareConnect`,
`squareAuthorize`, `cloverAuthorize` — zero matches.

The wizards use the credential-paste path instead (`access_token` text
field → `/api/pos/connect`). So the OAuth backend exists but is dead
code from the UI's perspective today.

### Clover OAuth — backend helper `src/clover/oauth.py`

**PARTIAL.** `CloverOAuthManager` class implements
`get_authorize_url`, `exchange_code`, `verify_token`, `revoke_token`,
`verify_webhook_signature`. The logic is real (`secrets.token_urlsafe`
CSRF state, HMAC-SHA256 webhook verification, `httpx` token exchange).

### Clover OAuth — backend routes

**MISSING.** No `/api/clover/authorize` or `/api/clover/callback` route
is defined anywhere in `src/api/`. Confirmed by grepping for
`prefix=` patterns and the `include_router` call list in
`src/api/app.py` (30 routers mounted, none Clover-OAuth).

This contradicts the docstring in `src/api/routes/pos_connections.py`:

> *"OAuth-based systems (Square, Clover) use their own /api/square/ and /api/clover/ routes for the authorization flow, then share the same connection status and sync infrastructure here."*

Today, Clover can only be reached through the credential-paste path
(`/api/pos/test-connection` + `/api/pos/connect` with
`access_token` + `merchant_id`).

### Toast OAuth

**N/A.** Toast uses partner-issued `client_id` / `client_secret` /
`restaurant_guid` (OAuth client-credentials, not user-redirect OAuth).
The backend handles this correctly in `_test_toast` and
`_run_toast_backfill` — no `/authorize` redirect is appropriate here.

---

## 3. Token storage

### Schema — `pos_connections` table

**WORKING.** Live in prod (Phase 1 census showed 1 row). Confirmed
columns referenced by code:

| Column | Notes |
|---|---|
| `id`, `org_id`, `provider`, `status` | Standard |
| `merchant_id`, `external_merchant_id` | Square `merchant_id`, Clover merchant id |
| `access_token_encrypted`, `refresh_token_encrypted`, `token_expires_at` | OAuth path |
| `credentials_encrypted` (JSONB) | Multi-field credentials for credential-paste path. Added by `supabase/migrations/20260511_pos_credentials_encrypted.sql`. |
| `location_ids` (jsonb) | Square locations |
| `historical_import_complete`, `last_sync_at`, `last_error` | Sync state |
| `created_at`, `updated_at` | |

`pos_connections` is created in an earlier base migration not in this
repo (likely `20260429_001_business_accounts.sql` — confirmed it's the
target of subsequent ALTERs). The 2026-05-11 migration adds
`credentials_encrypted` + a `(status, historical_import_complete, last_sync_at)`
partial index for scheduler lookups.

### Encryption — `src/security/encryption.py`

**WORKING.** AES-256-GCM via `cryptography.hazmat`. Key from
`ENCRYPTION_KEY` env (32-byte hex). Versioned ciphertext format
(`v1:nonce:ct:tag`). Used uniformly by both OAuth callback and
credential-paste paths.

### Migration tree split (mild PARTIAL)

There are two coexisting POS migration sets:
- `src/db/migrations/006_pos_connection_tracking.sql` — adds
  `pos_system_id`, `pos_connection_status`, `pos_credentials` JSONB to
  `leads` and `merchants` tables. Older.
- `supabase/migrations/20260504_pos_system_tracking.sql` +
  `20260511_pos_credentials_encrypted.sql` — adds POS tracking to
  `organizations`, creates `pos_waitlist`, creates the
  `pos_coverage_stats` / `pos_waitlist_stats` views, extends
  `pos_connections`. Newer.

The `supabase/migrations/` set is the authoritative one in prod (the
Phase 1 census confirmed `pos_connections`, `pos_waitlist`, etc. exist
on `organizations`, not `merchants`). The older
`src/db/migrations/006_*` adds the same fields to a `merchants` table
that doesn't appear in the prod table list. Code paths reading
"pos_connections" rely on the supabase set.

### Rep attribution

**MISSING.** No `pos_connections` column captures **who connected**
the POS:
- `created_by_rep_id`, `sales_rep_id`, `connected_by`, `concierge_rep_id`
  — none of these exist in the schema or the code that inserts into
  `pos_connections` (verified in both `oauth.py` and
  `pos_connections.py`'s `connect_pos`).
- `supabase/migrations/20260512_sales_reps_table.sql` exists (so a
  `sales_reps` table is presumably present) but the link from a
  pos_connection row back to a rep is not modelled.

For a concierge beta this is the gap that breaks commissionable
attribution and "who set this account up" support flows.

---

## 4. Ingestion

### Backend sync engines

**WORKING (per-provider).**
- `src/integrations/base/sync_engine.py` — abstract `BaseSyncEngine` with
  `run_initial_backfill` and `run_incremental_sync` contracts, a shared
  `SyncProgress` channel.
- `src/square/sync_engine.py` — `SyncEngine` for Square Orders +
  Customers + Catalog.
- `src/toast/sync_engine.py` — `ToastSyncEngine` (used by
  `_run_toast_backfill`).
- `src/clover/sync_engine.py` — `CloverSyncEngine`.
- `src/services/pos_connectors/rest_connector.py` — `GenericRESTConnector`
  for tier-3 providers driven by `registry.SYSTEM_CONFIGS`.

### Backend backfill / incremental workers

- `src/workers/backfill.py` — `run_backfill(access_token, org_id, connection_id)`.
  **Called from Square OAuth callback** (`oauth.py:230-237`) as a
  FastAPI background task. WORKING when the OAuth path is exercised
  (but the OAuth path isn't exercised from the UI — see §2).
- `src/workers/incremental_sync.py` — `run_incremental_sync(...)`.
  Designed to run every 15 minutes. NOT a Celery task. NOT scheduled
  anywhere. Plain async function.
- `src/workers/token_refresh.py` — token refresh worker. NOT a Celery
  task. NOT scheduled.
- `src/workers/tasks.py` — `sync_pos_data(self, org_id, pos_type='square')`
  IS a Celery task (`@app.task`, `max_retries=3`, `rate_limit=8/s`).
  Invoked inside `nightly_analysis` workflow via
  `chain(sync_pos_data.si(oid, pos), run_analysis.si(oid))` for all
  active orgs.

So **periodic POS sync exists** but only via the nightly chord, not via
a dedicated 15-min `beat_schedule` entry. The incremental_sync worker
file is effectively unwired (only directly callable from manual
trigger `/api/pos/sync/{org_id}/{pos_system}`).

### `/api/pos/connect` — auto-trigger of initial sync

**PARTIAL.** Look at `pos_connections.py:_connect_pos` (lines 215–320):

| Provider | After saving credentials, does it kick off backfill? |
|---|---|
| Toast | YES — `background_tasks.add_task(_run_toast_backfill, ...)` |
| Square | NO — the elif at line 304 *explicitly excludes* `square` and `clover` |
| Clover | NO — same |
| Other API (tier-3) | YES — `background_tasks.add_task(_run_generic_backfill, ...)` |
| CSV-only | N/A (separate `/upload-csv` endpoint) |

So if a rep connects Square via the credential-paste path (the only
path the UI exercises today), the connection record is created with
encrypted tokens, but `historical_import_complete` stays `false` until
a manual `/api/pos/sync/{org_id}/square` call, the nightly
`sync_pos_data` task fires, or the OAuth-callback path is used
(which the UI never does). Same for Clover.

The likely reasoning was "OAuth paths run their own backfill from the
callback". That's true for Square. It's *not* true for Clover (no
callback wired). And it's wrong for the wizard's credential-paste
path, where there's no callback at all.

### Webhooks

**WORKING.** `src/square/webhook_handlers.py` exists; the
`webhook_router` is mounted in `app.py`. Not verified end-to-end but
the wiring is present.

---

## 5. Canonical schema / normalization

### `src/services/pos_connectors/normalizer.py`

**WORKING (with caveats below).** `normalize_transaction(raw, system_key, org_id, location_id)`
produces a dict against `MERIDIAN_TRANSACTION_SCHEMA`. Maps wide keys
(`total`, `totalAmount`, `grand_total`, `Total`, `RO Total`, …) to a
single canonical field. Handles UNIX seconds + millis, multiple ISO
formats, MM/DD/YYYY, etc. Has automotive (VIN, labor hours,
technician, parts/labor split, year decode) and cannabis (METRC tag,
compliance ID, THC/CBD, batch) extensions.

### Canonical-schema gaps

**PARTIAL.** Two fields appear in the normalizer output but are NOT
present in the production `transactions` schema (per Phase 1
PostgREST recon):

| Field | In normalizer? | In prod `transactions` table? |
|---|---|---|
| `customer_id` | YES (`_extract_string` against `customer_id, customerId, guestId, patron_id`) | **NO** |
| `customer_name` | YES | NO |
| `currency` | **NO (not in schema at all)** | NO |

Implications:
- After a successful Square sync, `normalize_transaction` produces a
  dict with a `customer_id` populated from `o.get("customer_id")`. The
  subsequent `db.batch_upsert("transactions", normalized, ...)` either
  silently drops that column (Supabase REST will reject unknown
  columns, depending on PostgREST config) or fails the entire upsert.
  Net: **the existing pipeline cannot deliver `customer_id` end-to-end
  to the prod table**, which is also the precondition for any churn
  model.
- Currency is not modelled anywhere. Today the production cents column
  could mix CAD and USD on the same merchant if a Canadian merchant
  connects through the wizard. No automated detection, no per-org
  currency tag, no per-transaction currency. (The Canada wizard does
  use `monthly_price_cad_cents` for *invoicing* — but that's pricing,
  not transaction storage.)

---

## 6. Currency handling

**PARTIAL.**

Frontend:
- `POSSystemPicker` accepts `currency: 'USD' | 'CAD'` and the Canada
  wizard passes `currency="CAD"`. UI palette + display logic respects
  it.
- Canada wizard uses `formatCad` and `CAD_RATE` for billing amounts.

Backend:
- `_test_square` reads `merchant.country` (US in our test) but does
  not extract or persist `currency` from the Square `/v2/locations`
  payload (each location has a `currency` field).
- `pos_connections.py` `_run_toast_backfill` and `_run_generic_backfill`
  do not capture currency from the source.
- Normalizer has no currency field; no migration adds one to
  `transactions`.

Net: the UI tells the merchant "CAD" but everything downstream is
currency-blind. For a Canada/CAD beta this is a real risk — once
mixed, separating CAD vs USD lines retroactively is painful.

---

## Component-by-component status table

| Component | File / Route | Status |
|---|---|---|
| Frontend provider registry | `frontend/src/data/pos-systems.ts` | WORKING |
| POSSelectorPanel | `frontend/src/components/POSSelectorPanel.tsx` | WORKING |
| POSSystemPicker | `frontend/src/components/POSSystemPicker.tsx` | WORKING |
| US wizard connect step | `pages/customer/CustomerOnboardingWizard.tsx` | PARTIAL (Clover + Toast break in `connectPos`) |
| Canada wizard POS step | `pages/canada/portal/CanadaCustomerOnboardingWizard.tsx` | PARTIAL (calls `/api/pos/select` only — no auth, no token, no sync) |
| Canada Accounts "Sync POS" button | `pages/canada/portal/CanadaPortalAccountsPage.tsx` | STUB-UI-ONLY |
| Canada Accounts "Last POS sync" timestamp | same | STUB-UI-ONLY (hard-coded) |
| Frontend OAuth redirect | (none) | MISSING |
| Square OAuth backend | `src/api/routes/oauth.py` + `src/square/oauth.py` | WORKING (but dead-code from UI) |
| Clover OAuth backend helper | `src/clover/oauth.py` | PARTIAL (class only) |
| Clover OAuth routes | `/api/clover/{authorize,callback}` | MISSING |
| Toast partner-credential path | `src/toast/client.py`, `_test_toast`, `_run_toast_backfill` | WORKING |
| Credential-paste `/api/pos/test-connection` | `src/api/routes/pos_connections.py` | WORKING for Square + Toast + generic-REST; broken for Clover (needs `merchant_id` that wizard doesn't send) |
| Credential-paste `/api/pos/connect` | same | PARTIAL — does not auto-trigger backfill for Square/Clover |
| `/api/pos/select` bookkeeping | `src/api/routes/pos.py` | WORKING (but does NOT connect anything) |
| Token encryption | `src/security/encryption.py` | WORKING |
| `pos_connections` table | supabase migrations | WORKING |
| `pos_connections.connected_by_rep_id` | (none) | MISSING |
| 80-system registry | `src/services/pos_connectors/registry.py` | WORKING |
| Generic REST connector | `src/services/pos_connectors/rest_connector.py` | WORKING |
| CSV importer | `src/services/pos_connectors/csv_importer.py` | WORKING |
| Normalization layer | `src/services/pos_connectors/normalizer.py` | WORKING (with schema mismatch — see below) |
| `currency` in canonical schema | normalizer.py | MISSING |
| `customer_id` column on `transactions` | prod schema | MISSING |
| Square sync engine | `src/square/sync_engine.py` | WORKING |
| Toast sync engine | `src/toast/sync_engine.py` | WORKING |
| Clover sync engine | `src/clover/sync_engine.py` | WORKING |
| Backfill worker | `src/workers/backfill.py` | WORKING (when called) |
| Periodic incremental sync | `src/workers/incremental_sync.py` | PARTIAL (no `beat_schedule` entry; only callable via manual `/api/pos/sync/...` or the nightly chord) |
| Token refresh worker | `src/workers/token_refresh.py` | PARTIAL (not scheduled) |
| Webhook router | `src/api/routes/webhooks.py` + `src/square/webhook_handlers.py` | WORKING (wiring present, end-to-end not verified) |

---

## Phase 2 — Operational trace

### "Can a rep connect a real Square merchant today?"

Walk the call graph from the Canada wizard's connect button:

1. UI: rep enters Square Access Token in the wizard.
2. Wizard handler calls `connectPos('square', apiKey)` (auth.tsx:349).
3. `connectPos` POSTs `/api/pos/test-connection` with
   `{pos_system: 'square', credentials: {access_token: apiKey}}`.
4. Backend `_test_square` hits `https://connect.squareup.com/v2/merchants/me`
   with the token. If 200, returns success.
5. `connectPos` POSTs `/api/pos/connect` with same payload.
6. Backend encrypts `access_token`, upserts `pos_connections` row,
   updates `organizations.pos_system = 'square'`,
   `pos_connection_status = 'connected'`. **Does NOT trigger backfill**
   (the if/elif chain on lines 297–313 only auto-fires backfill for
   Toast and generic-REST).
7. Wizard reads `connectPos` return value (`null` = success), advances.

**Net answer: YES — auth + token storage works.** But:
- No initial backfill runs until someone calls
  `/api/pos/sync/{org_id}/square` manually, or the nightly
  `sync_pos_data` chord task runs.
- Even when backfill runs, the `customer_id` field that the normalizer
  produces is dropped at the table boundary (no column).
- No rep attribution stored.

### "Can a rep connect a real Clover merchant today?"

1. UI: wizard renders Clover with two fields (`api_key`, `merchant_id`).
2. Wizard handler calls `connectPos('clover', apiKey)` — sends only
   `access_token: apiKey` (the merchant_id is collected but not
   forwarded).
3. Backend `_test_clover` returns `{"success": false, "message": "Access token and Merchant ID required."}` because `merchant_id` is missing from `credentials`.
4. Frontend surfaces error; wizard does not advance.

**Net answer: NO.** Clover credential-paste is broken from the wizard.
And the OAuth path is missing routes entirely. So no Clover merchant
can be connected today through any UI surface.

### Can existing ingestion run dry against the operator's Square test token?

Possible in principle — call `_test_square(credentials={"access_token": SQUARE_ACCESS_TOKEN})`
and then `POST /api/pos/sync/...` once a `pos_connections` row exists.
Skipped here because (a) we cannot exercise it without writing rows to
prod (`pos_connections` + downstream `transactions` upserts), and (b)
the operator's Square account has 56 orders, 0% customer_id — even a
"successful" dry run would teach us nothing about customer-linked
ingestion.

### Other wired-but-broken or wired-but-stubbed surfaces

- Canada Accounts "Sync POS Data" button (UI animation only, no fetch).
- Canada Accounts "Last POS sync" (hard-coded "47 minutes ago").
- `pos_provider` displayed on the Canada Accounts tile is derived from
  `canada_leads`, not from the live `pos_connections` row.
- Token refresh worker exists but no Celery beat schedule.
- Standalone `incremental_sync.py` worker exists but is not registered
  as a Celery task and not scheduled (only `sync_pos_data` in the
  nightly chord covers this).

---

## Phase 3 — Gap report (the deliverable)

### Headline

The platform is **80% built and 20% wired**. The hard parts —
80-system registry, OAuth backend with HMAC state, AES-GCM token
storage, multi-provider sync engines, a 400-line canonical normalizer,
CSV fallback — are in place. The unwired 20% is exactly what stops a
beta:

1. The frontend never invokes the Square OAuth route.
2. Clover OAuth routes don't exist at all.
3. The wizard's credential-paste path only forwards a single field,
   breaking Clover and Toast.
4. The connect endpoint skips initial backfill for Square and Clover.
5. The destination `transactions` table has no `customer_id` column,
   so the normalizer's `customer_id` is silently dropped — which is
   exactly the gap that blocked Phase 1's churn-eval feasibility.
6. No currency tag anywhere in the canonical or stored schemas.
7. No rep attribution on `pos_connections`.

### Can a rep connect a real Square or Clover merchant today?

- **Square:** technically yes (auth + token storage works through the
  credential-paste path). Practically no for the eval/churn goal —
  the initial backfill doesn't auto-run, `customer_id` is dropped at
  the table boundary, and the OAuth flow (which is the right path for
  a real merchant, not a personal access token) is dead code from the
  UI.
- **Clover:** no. The wizard credential-paste path is broken
  (`merchant_id` not forwarded) and no OAuth routes exist.

**Single biggest blocking gap:** even after fixing the connect flow,
the `transactions` table has no `customer_id` column. Every other fix
unblocks UI/auth; this one unblocks the *value* of the ingestion
(churn, repeat-customer analytics, retention).

### What's already there vs what's needed

| Capability | Status |
|---|---|
| Provider-agnostic backend / 80-system registry | ✅ already there |
| Square OAuth adapter | ✅ already there (UI doesn't call it) |
| Clover OAuth adapter | ⚠️ helper class present; routes missing |
| Canonical normalization layer (no currency) | ⚠️ partial |
| Per-merchant encrypted tokens | ✅ already there |
| Rep attribution on connection | ❌ missing |
| Wizard connect step | ⚠️ partial (Square works credential-paste; Clover/Toast broken; OAuth not invoked) |
| CAD-aware schema | ❌ missing |
| Customer identity in `transactions` | ❌ missing |

### Prioritized "to make beta-operational"

In order of "unblocks the most for the smallest change":

**P0 — Schema fix (one migration, unblocks everything else)**
1. Add `customer_id TEXT` and `customer_email TEXT` to `transactions`
   (additive, nullable, reversible). Same for `transaction_items` if
   the join column matters there. Without this, no churn / no
   per-customer analytics no matter how good the connector is.
2. Add `currency CHAR(3)` to `transactions`, default `'USD'`, populated
   by the connector from the Square location's `currency` field (or
   the merchant's `country`). For Canada beta this prevents mixing.
3. Add `connected_by_rep_id` (UUID nullable, FK to `sales_reps`) to
   `pos_connections`. Lets the concierge model track who connected
   each merchant.

**P1 — Fix the wizard credential path (small frontend change)**
4. Update `connectPos(provider, credentials)` to accept a `credentials`
   object instead of a single `apiKey`, and have the wizard pass the
   right shape per provider (`{access_token, merchant_id}` for Clover;
   `{client_id, client_secret, restaurant_guid}` for Toast). This
   immediately unblocks Clover and Toast credential connections.

**P1 — Trigger backfill for Square credential-paste**
5. In `_connect_pos` (pos_connections.py), if provider is `square` or
   `clover` and we have a token, fire `_run_square_backfill` /
   `_run_clover_backfill` as a background task. Mirrors what Toast and
   generic-REST already do.

**P2 — Real OAuth UX**
6. Add a "Connect with Square" button in the wizard that redirects to
   `/api/square/authorize?org_id=...`. This is the right flow for real
   merchants; the credential-paste path is for power users only. The
   backend route is already there.
7. Mount Clover OAuth routes (`/api/clover/authorize`,
   `/api/clover/callback`) that mirror the Square pattern, using the
   existing `CloverOAuthManager`.

**P2 — Canada Accounts page real sync**
8. Wire the "Sync POS Data" button to
   `POST /api/pos/sync/{org_id}/{pos_system}`. Replace the hard-coded
   "Last POS sync" with the value from
   `pos_connections.last_sync_at`.

**P3 — Operational hygiene**
9. Register `incremental_sync` as a Celery task and add a
   `beat_schedule` entry every 15 min. Today only the nightly chord
   triggers sync.
10. Register `token_refresh` as a Celery task on a daily cadence (Square
    refresh tokens expire after 30 days; missing this risks a silent
    cliff).

### Canadian/CAD beta isolation

The CAD path already isolates billing/UI (CAD pricing, CAD palette,
"en-CA" date formats). The isolation that does **not** exist:
- Transaction storage has no currency tag, so a Canadian merchant's
  receipts and an American merchant's receipts share a column. P0.3
  above fixes this.
- The `_test_square` business-type detector calls
  `_mcc_to_business_type` — fine — but does not branch on `country`,
  so a Canadian Square merchant's MCCs get mapped through the same
  US-centric table. Low-risk for the beta but worth noting.

### Known identity-schema gap (carried forward from Phase 1)

The Phase 1 recon already established the production `transactions`
table has no customer-identity column. This audit identifies the
upstream cause: even though the normalizer fills `customer_id`, the
table boundary drops it. Closing P0.1 is the prerequisite for the
"smarter models" track — without it, no churn evaluation against real
Meridian-pipeline data is meaningful.

---

## Files referenced (audit footprint)

Backend:
- `src/api/routes/oauth.py` (Square OAuth)
- `src/api/routes/pos.py` (selection + waitlist)
- `src/api/routes/pos_connections.py` (test / connect / sync / disconnect)
- `src/api/app.py` (router mounting — Clover OAuth not in list)
- `src/clover/oauth.py` (helper only, no routes)
- `src/security/encryption.py` (AES-256-GCM)
- `src/services/pos_connectors/registry.py` (80-system map)
- `src/services/pos_connectors/normalizer.py` (canonical schema)
- `src/services/pos_connectors/rest_connector.py` (generic adapter)
- `src/integrations/base/sync_engine.py` (abstract sync)
- `src/square/sync_engine.py`, `src/toast/sync_engine.py`, `src/clover/sync_engine.py`
- `src/workers/backfill.py`, `src/workers/incremental_sync.py`,
  `src/workers/token_refresh.py`, `src/workers/tasks.py`,
  `src/workers/celery_app.py`
- `supabase/migrations/20260504_pos_system_tracking.sql`,
  `supabase/migrations/20260511_pos_credentials_encrypted.sql`,
  `supabase/migrations/20260512_sales_reps_table.sql`,
  `src/db/migrations/006_pos_connection_tracking.sql`

Frontend:
- `frontend/src/data/pos-systems.ts` (provider registry, 4,740 lines)
- `frontend/src/components/POSSelectorPanel.tsx`
- `frontend/src/components/POSSystemPicker.tsx`
- `frontend/src/lib/auth.tsx` (`connectPos`)
- `frontend/src/pages/customer/CustomerOnboardingWizard.tsx`
- `frontend/src/pages/canada/portal/CanadaCustomerOnboardingWizard.tsx`
- `frontend/src/pages/canada/portal/CanadaPortalAccountsPage.tsx`

No prod data was written. No customer data was sent to any external
LLM/API. No pm2 services, PoolDrop, qwen, Postal, or the US→Viktor
redirect were touched.
