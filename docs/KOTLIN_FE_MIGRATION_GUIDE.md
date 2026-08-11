# Frontend Migration Guide — Kotlin Cookie-Session Cutover

Status: PLANNING 2026-08-11 · Companion: [KOTLIN_USER_PORT_PLAN.md](./KOTLIN_USER_PORT_PLAN.md)

## The principle

After cutover the SPA **never handles JWTs**. The Kotlin backend verifies
credentials against Supabase Auth and owns the session via JDBC-backed cookies.
Every `fetch` to the backend needs `credentials: 'include'`; the SPA has no token
to attach and nothing to refresh. Cutover happens in a nighttime maintenance
window (Nathan's call, 2026-07-28) — backend endpoints land first, frontend flips
in one coordinated change.

## Call-by-call replacement map

### `src/lib/auth.tsx` (merchant auth)

| Today (Supabase client) | After cutover |
|---|---|
| `auth.signInWithPassword` | `POST /api/auth/login` |
| `auth.signUp` + RPC `create_business_for_user` | `POST /api/auth/signup` (no token) — one transactional call |
| `auth.signUp` + RPC `redeem_access_token` (localStorage token) | `POST /api/auth/signup` with `accessToken` in the body — drop the localStorage caching |
| RPC `validate_access_token` | `GET /api/onboarding/token/{token}` |
| `auth.signOut({scope:'local'})` | `POST /api/auth/logout` (server sessions are per-device; local-only semantics preserved) |
| `auth.getSession` / `onAuthStateChange` (boot) | `GET /api/auth/me` on app load: 200 → logged in, 401 → login screen. Keep the 5s timeout guard. |
| RPC `is_admin` (`checkAdmin`) | `isAdmin` field on `/me` |
| `from('sales_reps')` (`checkIsSalesRep`) | `isSalesRep` field on `/me` |
| `from('businesses')` by `owner_user_id` (`fetchBusinessForUser`) | `businesses[]` on `/me` |
| `from('organizations')` by email (legacy fallback) | **Not ported.** One-off SQL backfill for stragglers instead |
| `auth.resetPasswordForEmail` | `POST /api/auth/forgot-password` |
| `auth.updateUser({password})` in `PASSWORD_RECOVERY` | `POST /api/auth/reset-password` with the recovery token from the email-link URL fragment (the one raw Supabase token the SPA still touches) |

The `PASSWORD_RECOVERY` branch of `onAuthStateChange` becomes URL-fragment parsing
on the reset landing page (Supabase puts `access_token` + `type=recovery` in the
fragment; the backend never sees fragments, so the SPA must forward it).

**Cutover-time hardening — token-hash recovery flow.** Today's fragment style puts
a live session token in the URL (fragment-only, so never server-visible, but it
sits in browser history and is XSS-readable, and stays valid ~1h; the backend now
revokes it after a successful reset). The stronger pattern: customize the Supabase
recovery email template to carry `{{ .TokenHash }}` instead of a session, land on
the reset page with only that hash, and have the backend exchange it server-side
(`POST /auth/v1/verify`, `type=recovery`) before updating the password. No session
token ever appears in a URL and the emailed credential is single-use. Needs: email
template change (dashboard in prod, `config.toml` locally) + a `tokenHash` variant
of `POST /api/auth/reset-password`. Do this when the reset page moves off
supabase-js at cutover.

### `src/lib/sales-auth.tsx` (rep auth)

Same mapping: `signInWithPassword` → login, `signOut` → logout,
`resetPasswordForEmail` → forgot-password, `auth.getUser` → `/me`.
Rep identity comes from `isSalesRep` + rep profile on `/me` (or a rep-scoped
endpoint in a later slice).

### Settings pages (US/Canada `PortalSettingsPage`)

- `from('sales_reps').update({name, phone})` → needs a Kotlin rep-profile
  endpoint (rep slice — not user_port).
- `auth.updateUser({password: pw})` (change password while logged in) → needs
  `POST /api/auth/change-password` (session-authenticated; NOT the same as
  reset-password). **Gap found while writing this guide — now in user_port PR 2.**

## What ceases to exist at cutover

- `access_token`/`refresh_token`/`expires_in` handling, supabase-js auto-refresh,
  token persistence — replaced by cookie session expiry. No refresh endpoint.
- `TOKEN_STORAGE_KEY` localStorage invite-token caching.
- The `organizations` fallback and its localStorage `OrgProfile` mirror (org data
  comes from `/me`; decide then whether to keep a localStorage render cache).

## THE CUTOVER BLOCKER LIST — direct Supabase data access that rides the user's JWT

When the SPA stops holding a Supabase session, **every RLS-authenticated direct
table/storage/realtime call breaks (401/empty)**. Each must either move behind a
Kotlin endpoint before the flip, or be confirmed anon-safe. Inventory
(2026-08-11, `grep .from(` across `frontend/src`):

| Table (uses) | Where | Likely home |
|---|---|---|
| `sales_reps` (9) | sales-auth, settings, leads services | Rep slice |
| `us_leads` (7) / `canada_leads` (7) | us/canada-leads-service (+ realtime `.channel`) | Leads slice — realtime needs a backend push or polling story |
| `business_locations` (5) | onboarding wizards | Onboarding slice |
| `spaces` (3) / `space_zones` (2) | spaces-service | Spaces slice |
| `schedules` (3) / `schedule_uploads` (3) / `schedule_staff` (1) | wizards, schedule pages | Scheduler slice |
| `rep_training_progress` (3) / `rep_conduct_signatures` (2) | training-progress | Rep slice |
| `products` (3) / `inventory_document_uploads` (3) | onboarding wizard | Onboarding slice |
| `business_users` (2) | wizard staff step (placeholder-email roster rows) | Team slice — see staff-accounts section of the plan doc |
| `organizations` (2) / `businesses` (1) | auth.tsx | Dies with `/me` (this slice) |
| `recruiters` (1) | careers | Careers slice |
| Storage: `schedules` bucket uploads; realtime: leads channels, `useUnreadNotifications` | wizards, leads, notifications | Per-slice; storage uploads likely become backend-signed |

Rule of thumb: **auth cutover is gated on the last RLS-dependent read in any page
a logged-in merchant/rep actually uses.** Track this table; shrink it per slice.

## Sequencing

1. Backend slices land behind the existing surface (SPA untouched, RPCs intact).
2. FE work per slice can adopt Kotlin endpoints incrementally ONLY where the call
   doesn't depend on the Supabase session existing (e.g. token validate).
3. The auth flip itself (login/signup/logout/me/boot flow + `credentials:
   'include'` + CORS/SameSite config) is one coordinated change in the maintenance
   window, after the blocker table above is empty.
4. Prereq: `SPRING_SESSION` DDL migration on staging/prod Supabase.
