# Kotlin User-Functionality Port — Plan (branch `personal/nwong/user_port`)

Status: PLANNED 2026-08-11 · Owner: Aidan · Reviewer: Nathan
Companion doc: [KOTLIN_FE_MIGRATION_GUIDE.md](./KOTLIN_FE_MIGRATION_GUIDE.md)

## Context

The Kotlin backend (`backend/`) owns sessions via JDBC-backed cookies (spring-session);
the SPA never handles JWTs after cutover. Already ported: portal resolve/generate,
`/api/auth` signup/login/me/logout (#423, #434, #435, #437). `AuthController.login`
still sets a placeholder identity (`dummy_user_id_<email>`, empty business list) —
this slice replaces that with real identity and ports the rest of the user surface.

## Current state — the same functionality lives in THREE places

### 1. Python FastAPI `src/auth/router.py` (`/api/auth/*`)

| Endpoint | What it does | Disposition |
|---|---|---|
| `POST /register` | Supabase signup + `display_name`/`org_id`/`role` in user_metadata; starter-credit grant if `org_id` | **DEAD — zero callers anywhere.** Port intent only (see unified signup) |
| `POST /login` | Password grant → returns `access_token`/`refresh_token`/`expires_in` + user summary | Superseded by Kotlin cookie-session login (no tokens returned) |
| `POST /forgot-password` | Supabase `/recover` with `PASSWORD_RESET_REDIRECT_URL` override (Supabase site_url is a stale Vercel URL). Always generic success (anti-enumeration); 429/5xx logged loudly (built-in SMTP = 2 emails/hr) | **Port verbatim** (PR 2) |
| `POST /reset-password` | Email-link `access_token` + new password → PUT Supabase `/auth/v1/user` | **Port** (PR 2) |
| `GET /me` | Validate bearer JWT → id, email, org_id, location_id, role, display_name, is_verified | **Port + enrich** (PR 1) |
| `POST /verify` | Resend signup-confirmation email (same SMTP caveats) | **Defer** — rarely hit |

Roles: `owner`/`manager`/`staff` in Supabase `user_metadata`. No Python-side users table.

### 2. React → Supabase directly (`frontend/src/lib/auth.tsx`, `sales-auth.tsx`)

Full auth lifecycle client-side: `signInWithPassword`, `signUp`, `signOut(scope:'local')`,
`getSession`, `onAuthStateChange`, `resetPasswordForEmail`, `updateUser` (recovery),
plus RPCs `is_admin`, `validate_access_token`, `redeem_access_token`,
`create_business_for_user`, and direct reads of `businesses`, `organizations`
(legacy fallback), `sales_reps`. Call-by-call replacement map is in the FE guide.

### 3. Kotlin today

`signup` / `login` / `me` / `logout` exist, but `me` returns only the email and
login sets dummy identity (`AuthController.kt` TODO).

## Why there were three signup paths (archaeology, verified 2026-08-11)

1. **Python `/api/auth/register`** — original fastapi-users-era design where the
   backend owned auth. The SPA never adopted it; zero callers. Its starter-credit
   grant is unreachable — credits are actually granted post-login via the separate
   idempotent `POST /api/credits/starter-grant/{merchant_id}` (ledger-checked).
2. **React self-serve** — merchant walks up: `signUp` then RPC
   `create_business_for_user`. Two non-atomic steps; RPC failures are only
   `console.warn`ed → orphaned auth users with no business are possible.
3. **React invite-token (the sales motion)** — rep pre-creates the business and
   generates a token (`admin_generate_token`); customer validates
   (`validate_access_token`, token cached in localStorage, "you're joining X" UI),
   signs up, then `redeem_access_token` binds `owner_user_id` to the pre-created
   business (rep attribution + pre-filled data preserved).

**Two real use cases (self-serve, invite), one dead path.**

## How staff accounts are created today (NOT self-signup)

Staff never self-register. Two paths exist, and they are inconsistent:

1. **Real logins — Team Management page** (`frontend/src/lib/team-api.ts` →
   `POST /api/team-admin/members`, `src/api/routes/team_admin.py`): server creates
   the Supabase auth user via the **admin API** with a random temp password,
   `email_confirm: true`, `must_reset_password: true`, RBAC-normalized role in
   metadata; upserts the `business_users` row (unique `business_id,email`) with
   sanitized permissions, invite audit trail, `invite_status`. If the email already
   has an auth user it links WITHOUT resetting the password. Creating a second
   `owner` is rejected.
2. **Login-dead roster rows — onboarding wizards** (US/Canada
   `CustomerOnboardingWizard` "staff" step): inserts `business_users` rows with
   **fabricated `name@placeholder.local` emails, no auth user, no `user_id`**.
   Scheduling/roster display only; these staff can never log in, and when the same
   human is later properly invited they appear twice (real email vs placeholder).

**Not in this slice**: porting team-admin members CRUD is its own future slice
(flag for Nathan). But PR 1's login identity MUST resolve `business_users`
memberships correctly for staff created via path 1 (user_id linkage, role,
permissions).

## Target Kotlin surface — 8 endpoints (collapsed from ~12)

| Endpoint | Behavior |
|---|---|
| `POST /api/auth/signup` | **Unified + transactional.** Optional `accessToken`: present → validate + redeem + bind `owner_user_id` to pre-created business; absent → create `businesses` row. Carries `displayName`/`businessName` + extra metadata. No session issued when email confirmation is pending (SPA shows "check your email", then user logs in — matches existing `__confirm_email__` branch). Kills the orphan-user window. |
| `POST /api/auth/login` | Existing cookie-session login + **real identity**: resolve Supabase user → `business_users`/`businesses` memberships → session `USER_ID` + `BUSINESS_IDS`; bump `last_login_at`/`login_count`. |
| `POST /api/auth/logout` | Existing. Server-side session invalidation is inherently per-session ⇒ preserves the SPA's `scope:'local'` semantics (other devices stay logged in). |
| `GET /api/auth/me` | Enriched camelCase profile: `id, email, displayName, role, orgId, locationId, isVerified, isAdmin, isSalesRep, businesses[]`. Absorbs the `is_admin` RPC, `sales_reps` check, and `businesses` lookup (3 FE round-trips → 0). |
| `POST /api/auth/forgot-password` | Port with redirect override + anti-enumeration + 429/5xx ops logging (keep verbatim — hard-won behavior). |
| `POST /api/auth/reset-password` | Recovery token from the email-link URL fragment + new password. The ONE place the SPA still touches a raw Supabase token (backend never sees the fragment otherwise). |
| `POST /api/auth/change-password` | **New — gap found in FE guide.** Logged-in password change (settings pages currently call `auth.updateUser` directly). Session-authenticated: use the session's Supabase token to PUT `/auth/v1/user`. Distinct from reset-password (no recovery token). |
| `GET /api/onboarding/token/{token}` | Port of `validate_access_token`: real/unexpired/unredeemed + pending business name/owner for the pre-signup UI. Redeem itself folds into signup. |

**Deliberately not ported**: token-refresh machinery (cookie sessions replace it
entirely); `organizations`-by-email fallback (legacy shim — run a data check for
active users with an `organizations` row but no `businesses` row, backfill with
one-off SQL instead of carrying the fallback); `POST /verify` resend (deferred);
Supabase RPCs stay in place untouched so the current SPA keeps working until cutover.

## PR breakdown (granular, per backend/AGENTS.md)

- **PR 1 — Real session identity.** Hand-rolled `JdbcClient` repos
  (`BusinessUserRepository`, `AdminUserRepository`, `SalesRepRepository` —
  interface + Impl, explicit SQL, schema classes under `repository/schema`);
  `UserIdentityService`; login populates real `USER_ID`/`BUSINESS_IDS`; enriched
  `/me`. Kills the `AuthController` dummy-identity TODO.
- **PR 2 — Password lifecycle.** forgot-password / reset-password /
  change-password in `SupabaseAuthService`; all Supabase responses as typed
  POJOs (never `Map`).
- **PR 3 — Unified signup + token validate.** Transactional signup (both use
  cases), `GET /api/onboarding/token/{token}`. Explicit SQL in Kotlin
  transactions — do NOT call the PostgREST RPCs.
- **PR 4 — (thin) signup metadata polish.** Whatever metadata passthrough remains
  after PR 3. Starter credits stay a separate endpoint pattern (credits slice ports
  later); no stub needed inside signup.

## Deferred backlog (agreed 2026-08-11 — "fix at a later time")

- **Login rate limiting** — Python schema has `login_attempts` +
  `check_login_rate_limit()`; Kotlin login has nothing. Bread-and-butter CC6
  control; own slice.
- **Audit logging / observability slice** — Micrometer/Prometheus + structured
  auth-event trail (promised 07-30, not started).
- **Narrow the CSRF ignore-list** — `/api/auth/**` is fully CSRF-exempt but now
  contains session-authenticated state-changing POSTs (change-password);
  SameSite=Lax is the only guard.
- **Token-hash recovery flow** — see FE guide (cutover-time).
- **Staff/team-admin slice** — port `team_admin.py` members CRUD; reconcile
  wizard placeholder-email roster rows.
- **`user_profiles` consolidation** — docs/proposals/user-profiles-consolidation-2026-08.md
  (needs migration + backfill + drift reconciliation).
- **`POST /verify` resend** — deferred convenience endpoint.
- **SOC 2 framing** — ~52% ready, never say "certified"; this backend improves
  CC6 posture but certification is org-level machinery.

## Prereqs / standing notes

- `SPRING_SESSION` DDL (`backend/scripts/sql/init-local-db.sql`) must reach
  staging/prod Supabase as a migration before any cutover
  (`initialize-schema=embedded`).
- Wire format: camelCase (decided 2026-07-28). Backend first, then frontend;
  prod cutover in a nighttime maintenance window (auth flips JWT → cookie).
- Conventions: controller→service→repository, DTOs at edges, `ktlintFormat`,
  `unitTest`/`integrationTest`, OpenAPI `@Tag`/`@Operation` on every endpoint,
  FLAG any modification of existing code in the PR.
- Test-resources shadow `application.yml` — new `@Value` props must also be
  declared in `src/test/resources` or `@SpringBootTest` dies.
