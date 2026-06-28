# Control CC6.1-TENANT — API-tier Tenant Isolation

**Criterion:** CC6.1 (Logical Access). **Owner:** Aidan Pierce. **v0.1 — 2026-06-28.**

## Objective
At the API tier, the authenticated tenant is derived **server-side only** and a client can never act on another
tenant's data by supplying a tenant identifier. Never trust client-supplied tenant identifiers.

## Implementation
- **Identity from the JWT, not the request.** Tokens are verified server-side by calling Supabase
  `/auth/v1/user` (`src/api/auth.py:42-62`); the user id used for membership checks comes only from the
  verified token. A client cannot supply a different user id.
- **`org_id` resolution + membership check.** `require_org_access` resolves `org_id` from query/path **and**
  body (`_org_id_from_body`, `src/api/auth.py:142-225`) then verifies the JWT user is a member/owner of that
  org (`_check_org_membership`, `auth.py:87-139`). Non-members get 403.
- **Second BOLA layer.** `enforce_service_member(principal, org_id)` (`auth.py:313`) is called inside handlers
  guarded by `require_service_auth` (which otherwise accepts *any* valid merchant session). No-op for
  machine principals; membership check for user principals.

## Canonical remediated incident (CA-1/CA-2) — write this up for the auditor
**What broke:** `require_org_access` originally inspected only query/path params. POST handlers that passed
`org_id` exclusively in the JSON body bypassed the guard (it returned `None` → "no org param" no-op), enabling
**unauthenticated cross-tenant writes** (reproduced live: HTTP 200 on a cross-tenant POST).
**Fix:** body `org_id` is now resolved and membership-checked (`auth.py:142-225`); commit `dfd864e9`,
merged via `fix/main-cross-tenant-guard`.
**Verify:** `tests/api/test_tenant_isolation_bola.py` proves the denied path — non-member → 403, and the
mutation does **not** run (`assert db.updates == []`).

## Open gap (C1 — CRITICAL, R-02)
`enforce_service_member` is **not yet threaded into every** tenant-scoped `require_service_auth` handler.
Per `docs/SECURITY_SWEEP_2026-06-27.md:33-46`, the remaining endpoints span `phone_dashboard.py`,
`schedule.py`, `website.py`, `intelligence.py`, `stripe_connect.py`, `pos.py`. Until complete, any signed-up
merchant session can reach those endpoints for another org.

Also: `TENANCY_ENFORCEMENT_DISABLED=1` (`auth.py:213`) is an emergency rollback knob that, if set in prod,
silently allows non-members through (logs `TENANCY_WARN`). **Confirm it is absent/false in production.**

## Remediation (authored plan — Aidan merges)
**R2:** add `await enforce_service_member(principal, org_id)` as the first line of every tenant-scoped
service-auth handler; add a parametrized negative test per route (extend
`tests/api/test_tenant_isolation_bola.py`). Assert the side effect does not run, not merely the 403.

## Evidence pointer
`/compliance/evidence/CC6.1-TENANT/` — the guard code references, the existing BOLA test, and (after R2) the
per-route denial matrix. Independence from `CC6.1-RLS` is the point: API guard and DB RLS are **different
control planes** and must both deny.
