# Control CC6.1-RLS — Database Row-Level Security (least privilege)

**Criterion:** CC6.1 (Logical Access). **Owner:** Aidan Pierce. **v0.1 — 2026-06-28.**

## Objective
Every table holding financial, PII, or tenant data enforces least-privilege access at the **database** tier
via Supabase RLS, independent of the API tier — so that a compromised or bypassed API cannot expose
cross-tenant data. The RLS test suite is treated as a primary deliverable.

## Why this matters (defense in depth)
The API guard (`CC6.1-TENANT`) and RLS must **fail independently** (different control planes). If both depend
on the same assumption, "two layers" is one check with decoration. RLS is the backstop for any direct
PostgREST / Supabase-JS access carrying a valid `authenticated` JWT.

## Current state (verified against `origin/main`, HEAD 77bbf327)

### The anti-pattern — wide-open policies still present
Named "Service role full access" but **missing the `TO service_role` clause**, so they apply to the `public`
role (anon + authenticated). Verified present:

| Table | File:line | Data at risk |
|---|---|---|
| `vision_cameras`, `vision_traffic`, `vision_visitors`, `vision_visits` | `supabase/migrations/20260516_vision_cameras.sql:80-83` | footfall, re-ID `person_id`, demographics |
| `phone_agent_config` | `supabase/migrations/20260507_phone_agent.sql:82` | **`pos_access_token` (POS credential)** |
| `phone_call_logs` | `…20260507_phone_agent.sql:85` | call transcripts, `caller_phone` (PII) |
| `phone_orders` | `…20260507_phone_agent.sql:88` | customer name/phone/order |
| `sms_optout_tracking` | `…20260604_sms_optout_tracking.sql:54` | CASL opt-out + phone numbers |
| `schedule_staff`, `schedule_shifts`, `published_schedules` | `…20260522_schedule_tables.sql:60-62` | staff roster, hourly rates |

### Correlated findings
- **Camera P0 fix migration `20260624_camera_streaming_phase1.sql`** and its Postgres-level denial test
  `tests/e2e/test_camera_tenancy_rls.py` exist in git history but are **absent from `origin/main`** — so a
  `supabase db push` from main will never close the camera hole. (Confirmed by `ls` on HEAD.)
- **`get_user_org_id()`** is called by the `benchmark_snapshots` policy (`20260501_006_rls_security_fix.sql:30`)
  but is **never defined** in any migration → runtime error or silent deny.
- **`cline_*` / `merchant_health`** scope reads via `business_id = auth.uid()` (`20260501_005:124`) which never
  matches a real user UUID → silent deny of all rows.
- POS transaction tables (`square_/clover_/toast_transactions`) have RLS **enabled** but the authenticated
  SELECT policy is **commented out** (`20260618_pos_per_provider_phase2_cutover.sql:67`) → service-role only.

### Tables WITH correct org-scoped RLS (the good pattern to copy)
`businesses`, `business_users`, `business_locations` (`20260429_001:158-206`); `cpa_*` (`migrations/025`);
cross-reference tables via `current_setting('app.current_org_id')` (`20260511:104-114`).

## Implementation (authored, NOT applied — Aidan reviews/merges)
1. **R0 (verify first):** query live Supabase `pg_policies` to learn which wide-open policies are *actually*
   live (migration files ≠ live DB; the camera fix may have been applied off-main). Read-only.
2. **R1/R3 fix migration** (`/evidence/CC6.1-RLS/fix_rls_wideopen.sql`): for each table above —
   `DROP POLICY` the wide-open one; add a `TO service_role USING(true)` policy (backend writes) **plus** an
   org-scoped `TO authenticated` policy using the membership pattern
   (`org_id IN (SELECT org_id FROM business_users WHERE user_id = auth.uid())`), or service-role-only where no
   authenticated read is intended.
3. Restore the camera P0 migration + denial test to main.
4. Define `get_user_org_id()` or rewrite the policy; fix `cline_*` membership scoping.

## Adversarial verification (the negative test is the deliverable)
`/evidence/CC6.1-RLS/test_rls_cross_tenant.py` (and the SQL harness) proves the **denied path fails**: seed two
tenants, set the session to tenant A, assert A sees its own rows and **cannot** see/modify tenant B's rows, and
assert **zero** `pg_policies` rows with `qual = 'true'` remain on the sensitive tables. Wire into CI
(`.github/workflows/syntax-check.yml`) so the guard runs on every PR.

## Evidence pointer
`/compliance/evidence/CC6.1-RLS/` — policy inventory, fix migration, negative tests, and (after R0) the live
`pg_policies` snapshot. **Until R0 + R1/R3 land, this control is a CRITICAL open gap (R-01).**
