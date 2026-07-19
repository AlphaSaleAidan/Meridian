# View Hierarchy — Permissions & Visibility Architecture

**Status:** Living reference · Last reconciled against code: 2026-07-19 (branch `feat/recruiter-title-view-hierarchy`, base = main @ PR #354 merged)

This is the single source of truth for **who can see and do what** across Meridian's
surfaces. It maps every **role × surface × capability**, then reconciles that intended
model against the actual **route guards** (`src/api/routes/*`, `src/api/auth.py`,
`src/api/hierarchy.py`) and **Supabase RLS policies** (`supabase/migrations/*`,
`migrations/*`).

Two independent control planes enforce tenancy (defense-in-depth):

1. **API guards** (FastAPI `Depends`) — `require_jwt`, `require_service_auth`,
   `require_admin` / `require_admin_auth` / `require_admin_jwt`, `require_us_admin`,
   `require_org_access` (+ `_org_id_from_body`), `require_org_admin`,
   `enforce_service_member` / `require_org_member`, device-token guards.
2. **Postgres RLS** — per-table policies keyed on `auth.uid()` (owner/member) or
   `auth.email()` (sales-rep hierarchy). `service_role` bypasses RLS by design; the
   backend uses it and therefore MUST enforce tenancy in the API layer (plane #1).

---

## 1. Portals & the god view

| Surface | Who | Scope | Enforced by |
|---|---|---|---|
| **HQ (US) — god view** | Aidan Pierce (super-admin) + machine principals | ALL portals, ALL orgs, ALL reps, ALL commissions, ALL payouts | `require_admin` (X-Admin-Key) / `require_admin_auth` (key/service-token/`ADMIN_EMAILS`) |
| **US portal admin** | **Aidan Pierce only** (`apierce@alphasale.co`, `aidanpierce72@gmail.com`, `aidanpierce@meridian.tips`) | US orgs, US reps, US pricing/commissions | `require_us_admin` (US-scoped allowlist, `src/api/routes/us.py:59-88`) + frontend `US_ADMIN_EMAILS` (`frontend/src/lib/us-admins.ts`) |
| **Canadian portal admins** | **Aidan Nguyen + Enoch Cheung** | Canada orgs, Canada reps, Canada pricing/commissions | global `ADMIN_EMAILS` (`src/api/auth.py:26-32`) + hierarchy `is_admin` |
| **Business owner / manager / employee** | one business's team | scoped to a **single business** (org) | WS1 RBAC — see §3 (in-flight branch `feat/team-management`) |
| **Multi-location Hub (Command tier)** | a multi-location owner | that owner's **OWN orgs only** | org-membership per location (`_check_org_membership`) |

### Portal isolation (no cross-portal leak)

- **US admin is INTENTIONALLY narrower than the global admin list.** `require_admin_jwt`
  checks global `ADMIN_EMAILS` (which includes the Canada admins Enoch + Aidan Nguyen);
  US rep-management endpoints therefore gate on `require_us_admin`'s US-only allowlist so
  Canada admins cannot approve/reject/remove US reps. Documented and wired at
  `src/api/routes/us.py:67`.
- **Separate lead tables:** `us_leads` and `canada_leads` are distinct tables with no
  shared row pool → no cross-portal lead leakage at the data layer.
- **Separate pricing/commission structures:** plan tiers (`standard | premium | command`)
  and per-order fee floors differ by portal/currency (`migrations/036`, `042`;
  `src/billing/fee_terms.py`); commissions/payouts are per-rep and scoped by the sales
  hierarchy path.

---

## 2. Sales hierarchy (reps)

7-level org tree on `sales_reps` (`role` + `manager_id` + materialized `path`);
`src/api/hierarchy.py`, `supabase/migrations/20260716_sales_hierarchy.sql`.

| Level | Role | Sees (roster / leads / commissions) |
|---|---|---|
| 1 | `admin` | everything in their portal (all reps, all leads, all commissions) |
| 2 | `vp_sales` | own subtree + upline chain |
| 3 | `regional_manager` | own subtree + upline chain |
| 4 | `district_manager` | own subtree + upline chain |
| 5 | `office_manager` | own subtree + upline chain |
| 6 | `assistant_manager` | own subtree + upline chain |
| 7 | `sales_rep` | **self only** (fails CLOSED: no role/path ⇒ self-only) |

RLS keys the hierarchy on **`auth.email()` → `sales_reps.email`**, not `auth.uid()`
(the two ID systems differ). Managers see downline via materialized-path prefix scan;
admins see all.

---

## 3. Business RBAC (WS1 — in-flight `feat/team-management`)

Scoped **within one business** (`business_users` + `businesses.owner_user_id`):

| Role | Capability |
|---|---|
| **Business owner** | full control of their org: connect POS, manage team, billing, all dashboards |
| **Manager** | operational: dashboards, schedules, menu, spaces — no billing/ownership |
| **Employee** | task-scoped: assigned dashboards/schedules only |

Enforced by `_check_org_membership` (owner via `businesses.owner_user_id`; member via
`business_users` active row; global `ADMIN_EMAILS` for support). Role granularity
(owner/manager/employee gating within an org) is the deliverable of the in-flight
`feat/team-management` branch; this doc references it as the authoritative RBAC contract
for the business tier. The Multi-location Hub (Command tier) is an **owner-level** view
spanning that owner's own orgs only — it is membership-per-location, never a cross-tenant
grant.

---

## 4. Role × Surface × Capability matrix

Legend: ✅ full · 🟦 own-org/own-subtree only · 🔑 machine principal (admin key / service
token) · ➖ no access · 🌐 public (no auth).

| Surface (route prefix) | HQ / super-admin | US admin (A. Pierce) | CA admin (Nguyen/Cheung) | Business owner | Manager/Employee | Sales rep | Public | Guard |
|---|---|---|---|---|---|---|---|---|
| `/api/admin/*` | ✅ | ➖ | ➖ | ➖ | ➖ | ➖ | ➖ | router `require_admin` |
| `/api/payouts/*` (ledger) | ✅ | ✅¹ | ✅¹ | ➖ | ➖ | ➖ | ➖ | router `require_admin_auth` |
| `/api/training/*` | ✅ | ✅¹ | ✅¹ | ➖ | ➖ | ➖ | ➖ | router `require_admin` |
| `/api/us/rep-approve|reject|update` | ✅ | ✅ | ➖ | ➖ | ➖ | ➖ | ➖ | `require_us_admin` |
| `/api/us/rep-signup`, `/api/careers/*` | — | — | — | — | — | — | 🌐 (rate-limited) | `rate_limit_signup` |
| `/api/team/assign` | ✅ | 🟦² | 🟦² | ➖ | ➖ | ➖ | ➖ | `require_org_admin` |
| `/api/team/tree`, `/api/leaderboard` | ✅ | 🟦 | 🟦 | — | — | 🟦 | ➖ | `require_jwt` + hierarchy scope |
| `/api/dashboard/*`, `/api/analytics/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | router `require_org_access` |
| `/api/predictive/*`, `/api/inventory-docs/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | router `require_org_access` |
| `/api/spaces/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | 🌐³ | router `require_org_access` + `_authorize_space_access` |
| `/api/vision/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | router `require_org_access`; device heartbeat = device token |
| `/api/vision/ingest/*`, `/device/*` | 🔑 | — | — | 🟦 (device) | — | — | ➖ | `require_device_principal` + `enforce_org_match` |
| `/api/pos/select` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | `require_service_auth` + `enforce_service_member` |
| `/api/pos/waitlist` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | — | 🌐⁴ | public insert; org write gated on membership |
| `/api/pos/coverage|status` | ✅ | ✅¹ | ✅¹ | ➖ | ➖ | ➖ | ➖ | `require_admin` / `require_admin_auth` |
| `/api/pos-connections/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | router `require_org_access` + inline `require_org_member` |
| `/api/menu/*`, `/api/menu-ingest/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | 🌐 (public menu) | `require_service_auth` + `enforce_service_member` |
| `/api/schedule/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | `require_service_auth` + `enforce_service_member`/row-member |
| `/api/website/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | 🌐 (public site/order) | `require_service_auth` + `enforce_service_member` |
| `/api/content/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | 🌐 (models list) | `require_jwt` + `require_org_member` |
| `/api/billing/*`, `/api/onboarding/*` | ✅/🔑 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | ➖ | `require_service_auth`+org-scope / `require_admin_auth` |
| `/api/credits/*` | ✅ | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | 🌐 (packs) | `require_jwt`+`require_org_member`; grant/deduct = `require_admin_jwt` |
| `/api/intelligence/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | `require_service_auth`+`enforce_service_member`; train/evolution = `require_admin` |
| `/api/stripe-connect/*`, `/api/stripe/*` | 🔑 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | 🌐 (signed webhook) | `require_service_auth`+`enforce_service_member` |
| `/api/email/send` | 🔑 | 🟦 | 🟦 | 🟦 | — | — | ➖ | `require_service_auth`; org-scope when `org_id` present |
| `/api/portal/generate` | ✅ | ✅¹ | ✅¹ | ➖ | ➖ | ➖ | ➖ | `require_admin_auth` |
| `/api/portal/resolve/{token}` | — | — | — | — | — | — | 🌐 (token is the secret) | stateless signed token |
| `/api/cline/*`, `/api/vision/connect/*` | 🔑 | 🟦 | 🟦 | 🟦 | 🟦 | ➖ | ➖ | router/endpoint `require_org_access` |

Footnotes:
¹ Machine/global admin surfaces (payouts, training, portal-token) accept any
`ADMIN_EMAILS` member — both US and CA admins pass because these are cross-portal
platform-ops surfaces, not portal-scoped rep management. **Rep management is the surface
that is US-only via `require_us_admin`.**
² `require_org_admin` gates on `role=='admin'` OR the hierarchy allowlist, scoped to the
caller's tree.
³ `/api/spaces/{space_id}/model` and `/jobs/{job_id}` are opaque-id reads; write/status
routes are BOLA-guarded by `_authorize_space_access` (loads the row, matches org from the
authenticated session — never the request).
⁴ See Reconciliation gap R-1 (fixed on this branch).

---

## 5. RLS policy summary (data plane)

| Table group | Tenant key | RLS posture |
|---|---|---|
| `businesses`, `business_users`, `business_locations`, `onboarding_progress`, `support_tickets` | `owner_user_id` / `user_id` → `auth.uid()` | owner + active-member scoped |
| `sales_reps` | `auth.email()` → `email`; materialized `path` | hierarchy prefix-scan; legacy `WITH CHECK (true)` policies (`20260511`, `20260512`) **superseded** by `20260716_sales_hierarchy.sql` |
| `us_leads` / `canada_leads` | `rep_id` via `auth.email()` join | per-rep isolation (`20260628_*_isolation.sql`, `20260522_us_leads_rls.sql`); unassigned (`rep_id IS NULL`) visible to reps in-portal |
| `commissions`, `payouts` | `rep_id` + downline path | downline read; payout **ledger API** is admin-only (plane #1) |
| `phone_*`, `schedule_*` | `merchant_id` | `service_role`-only `FOR ALL USING(true)` (backend-only; anon/authenticated GRANTs revoked in `20260628_fix_phone_schedule_rls_anon_exposure.sql`) |
| `square/clover/toast_transactions` | `merchant_id` | per-provider isolation (`20260618_pos_per_provider_*`) |
| `vision_cameras/visitors/visits/traffic`, `camera_sites` | `org_id` → `auth.uid()` | org-scoped |
| `cline_*`, `agent_reasoning_chains`, `merchant_health` | `business_id` → `auth.uid()::uuid` | business-scoped + service-role |
| `content_*` | `merchant_id` | org-isolated (`migrations/025+`) |
| `merchant_credits`, `credit_ledger`, `credit_purchases` | `business_id` | wide-open policies **dropped** (`20260603_drop_wideopen_policies_*`) |
| compliance (`casl_consent_records`, `privacy_requests`, `breach_log`, `data_inventory`) | — | service-role write; `compliance_documents` public-read (legal docs, intentional) |

**`USING (true)` audit:** every remaining permissive policy is either (a) `TO service_role`
(safe — backend bypass, anon/authenticated revoked), or (b) public legal-document read.
The historically dangerous open lead/credit/sales-rep policies have all been superseded
or dropped. No `TO anon` write grant remains on tenant tables.

---

## 6. Reconciliation gaps

Method: enumerated every `@router.*` endpoint and its guard; identified endpoints where an
`org_id` / `merchant_id` / `business_id` is read from a **client-supplied request body or
multipart form** and checked whether membership is enforced (router `require_org_access` +
`_org_id_from_body`, inline `require_org_member`, or `enforce_service_member`). Each
candidate was **runtime-probed**, not just read.

### R-1 — `POST /api/pos/waitlist` unauthenticated cross-tenant org write — **FIXED (this branch)** · severity: LOW→MED

- **File:** `src/api/routes/pos.py:44` (pre-fix).
- **Class:** org_id-from-body. The endpoint is intentionally public (a prospect joins a
  waitlist by email, no JWT). It accepted an optional body `org_id` and then ran
  `UPDATE organizations SET pos_waitlist_email = <caller email> WHERE id = <body org_id>`.
  Any **unauthenticated** caller could stamp an arbitrary email onto **any** organization
  row — a cross-tenant write keyed on a client-supplied identifier.
- **Impact:** limited-field write (one column) / data-integrity + attacker-controlled value
  injection on a victim org. No cross-tenant *read*. `pos_waitlist_email` has no downstream
  reader in the app, which bounds the blast radius.
- **Fix:** the public `pos_waitlist` INSERT still runs for everyone; the privileged
  `organizations` UPDATE now only fires when the request carries a principal that is a
  **verified member** of that org (`_waitlist_can_write_org` → `_verify_supabase_token` +
  `_check_org_membership`, fail-closed). Non-members still get 200 (they joined the
  waitlist) but no foreign-org write occurs.
- **Test:** `tests/test_pos_waitlist_org_write.py` (RED before fix: unauthenticated write
  fired; GREEN after: member-stamp preserved, no-org public signup preserved).

### Verified SAFE (candidates that looked like gaps but are not)

- **`/api/spaces/process`, `/process-frames`, `/upload-splat`** (`spaces.py:114,156,227`)
  read `merchant_id` from a **multipart Form** field. Runtime-probed: router
  `require_org_access` resolves it via `_org_id_from_body`'s multipart branch →
  **401 unauthenticated, 403 cross-tenant.** Not a gap.
- **`/api/spaces/{space_id}/status|zones|model`** — BOLA-guarded by `_authorize_space_access`
  (PR #354). Covered by `tests/test_security_batch_20260719.py`.
- **`/api/email/send`** (`email.py:29`) — `require_service_auth` + `enforce_service_member`
  when `org_id` present. Org-less templates (e.g. `password_reset`) legitimately need no org
  scope. Not a gap.
- **`pos_connections` / `predictive` body-org endpoints** — resolved by CA-1/CA-2
  (`_org_id_from_body`) + inline `require_org_member`; pinned by
  `tests/test_security_batch_20260719.py`.
- **`/api/pos/select`, `/api/menu/*`, `/api/menu-ingest/*`, `/api/schedule/*`,
  `/api/website/*`, `/api/content/*`, `/api/billing/*`, `/api/intelligence/*`,
  `/api/stripe-connect/*`, `/api/vision/ingest/*`** — every body/path `org_id`/`merchant_id`
  is followed by `enforce_service_member` / `require_org_member` / device `enforce_org_match`.

### Open items flagged for Aidan (NOT auto-fixed — ambiguous / policy calls)

- **Footnote ¹ surfaces (payouts ledger, training, portal-token generation)** accept both
  US and CA admins via global `ADMIN_EMAILS`. That is correct **iff** these are meant to be
  cross-portal platform-ops. If payout/commission *visibility* must itself be portal-siloed
  (US payouts hidden from CA admins and vice-versa), that is a deliberate policy change to
  `require_admin_auth` scoping — flagged, not changed.
- **`sales_reps` is a single shared roster** across both portals; isolation relies on
  `portal_context` + hierarchy path + `auth.email()`. If a hard US/CA table split is desired
  (matching the `us_leads`/`canada_leads` split), that is an architecture decision for a
  future ADR — flagged, not changed.
