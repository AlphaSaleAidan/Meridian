# Auth Hardening Plan — Critical Findings C-1, C-4, C-5

These three findings require frontend + backend changes and design decisions.
They were identified in the May 2026 security audit and intentionally NOT
auto-fixed because they would break the running app without coordinated updates.

---

## C-1: Admin Authorization via Client-Supplied Email (CRITICAL)

**Current state**: Admin endpoints (rep-approve, rep-reject, rep-update, rep-remove,
privacy export, breach log, compliance dashboard) check if a client-supplied
`admin_email` field matches a hardcoded `ADMIN_EMAILS` list. No cryptographic
proof the caller controls that email.

**Risk**: Any attacker can POST `{"rep_id": "...", "admin_email": "aidanpierce72@gmail.com"}`
to approve reps, delete reps, or export all personal data.

**Recommended fix** (pick one):

### Option A: X-Admin-Key Header (Quick fix, 1-2 hours)
- Generate a strong random secret, store as `ADMIN_API_KEY` env var on Railway
- All admin endpoints check `X-Admin-Key` header matches the secret
- Frontend sends the key in requests (stored in env var, not hardcoded)
- Add `X-Admin-Key` to CORS `allow_headers`
- Pro: Simple, fast to implement
- Con: Single shared secret, no per-admin audit trail

### Option B: Supabase JWT Verification (Proper fix, 4-6 hours)
- Extract JWT from `Authorization: Bearer <token>` header
- Verify JWT signature against Supabase JWT secret
- Extract user email from JWT claims
- Check email against ADMIN_EMAILS (or a `user_roles` table)
- Pro: Per-user identity, audit trail, integrates with existing Supabase auth
- Con: More complex, need JWT secret on Railway, frontend already sends tokens

### Option C: Supabase RLS + Admin Role (Best, 6-8 hours)
- Add `role` column to `sales_reps` or create `user_roles` table
- Backend verifies JWT, extracts user ID, checks role via RLS query
- Admin operations use the user's JWT (not service role key) where possible
- Pro: Defense in depth (RLS + app-level), per-user audit trail
- Con: Most complex, requires migration

**Recommendation**: Option B for now, migrate to C later.

---

## C-4: Unauthenticated Data Endpoints (CRITICAL)

**Current state**: These endpoints have ZERO authentication:
- `GET /api/canada/leads` — dumps all deal data
- `GET /api/canada/stats` — revenue/commission stats  
- `GET /api/canada/team` — rep names, emails, phone numbers, commission rates
- `GET /api/us/leads`, `/api/us/stats`, `/api/us/team` — same for US

**Risk**: PII (emails, phones), commission rates, and deal data publicly accessible.

**Recommended fix**:
1. Add `Depends(require_service_auth)` to all data endpoints (quick gate)
2. Frontend must send `Authorization` header with Supabase JWT on these calls
3. Backend validates JWT and checks the user's org_id matches the data requested

**Frontend changes needed**:
- `CanadaPortalTeamPage.tsx` — add auth header to `/api/canada/team` fetch
- `USPortalTeamPage.tsx` — add auth header to `/api/us/team` fetch
- `CanadaPortalLeadsPage.tsx` / `USPortalLeadsPage.tsx` — add auth headers
- `CanadaPortalDashboardPage.tsx` / `USPortalDashboardPage.tsx` — add auth headers

---

## C-5: Billing Endpoints Missing Authentication (CRITICAL)

**Current state**: These billing endpoints have no auth:
- `POST /api/billing/create-checkout`
- `POST /api/billing/create-invoice`
- `GET /api/billing/status/{org_id}`
- `POST /api/billing/update-payment-method`
- `POST /api/billing/notify-payment-failed`
- `GET /api/billing/invoice-url/{org_id}`

**Risk**: Unauthorized users can create checkout links, generate invoices, view
subscription status for any org, trigger payment failure emails.

**Recommended fix**: Add `Depends(require_service_auth)` to all billing endpoints.
The webhook endpoint (already fixed in this batch) is the only one that should
remain unauthenticated (but now properly validates signatures).

---

## H-3: Dashboard IDOR (org_id from query param)

**Current state**: All dashboard endpoints accept `org_id` as a query parameter.
UUID format is validated, but there's no check that the caller owns that org.

**Recommended fix**: Extract org_id from the JWT claims instead of accepting it
as a query parameter. For admin use, verify JWT user has admin role before
allowing arbitrary org_id access.

---

## Implementation Priority

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | C-1 Admin auth (Option B) | 4-6h | Blocks all admin impersonation |
| 2 | C-4 Data endpoint auth | 2-3h | Blocks PII exposure |
| 3 | C-5 Billing auth | 1-2h | Blocks billing abuse |
| 4 | H-3 Dashboard IDOR | 2-3h | Blocks cross-tenant access |

Total estimated effort: 1-2 days of coordinated backend + frontend work.
