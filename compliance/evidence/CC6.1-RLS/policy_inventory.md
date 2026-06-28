# Evidence — CC6.1-RLS — RLS policy inventory & verification

**v0.1 — 2026-06-28.** Source-of-truth = migration files at `origin/main` (HEAD `77bbf327`).

## Wide-open policies present (the gap) — verified by grep on HEAD
`FOR ALL USING (true) WITH CHECK (true)`, named "Service role full access" but **no `TO service_role`** → apply
to the `public` role:

| Table | File:line |
|---|---|
| vision_cameras / vision_traffic / vision_visitors / vision_visits | `supabase/migrations/20260516_vision_cameras.sql:80-83` |
| phone_agent_config (holds `pos_access_token`) | `supabase/migrations/20260507_phone_agent.sql:82` |
| phone_call_logs / phone_orders | `…20260507_phone_agent.sql:85,88` |
| sms_optout_tracking | `…20260604_sms_optout_tracking.sql:54` |
| schedule_staff / schedule_shifts / published_schedules | `…20260522_schedule_tables.sql:60-62` |

Correlated: camera P0 fix migration `20260624_camera_streaming_phase1.sql` + `tests/e2e/test_camera_tenancy_rls.py`
**absent from main** (verified by `ls`); `get_user_org_id()` undefined (`20260501_006:30`); `cline_*` scope via
`business_id = auth.uid()` never matches (`20260501_005:124`); POS txn tables' authenticated SELECT commented out
(`20260618_..._phase2_cutover.sql:67`).

## Correct pattern present (good — copy this)
`businesses`/`business_users`/`business_locations` org-scoped (`20260429_001:158-206`); `cpa_*` (`migrations/025`);
cross-reference tables via `current_setting('app.current_org_id')` (`20260511:104-114`); credit tables already
remediated to service-role-only (`20260603_drop_wideopen_policies_subgroup_a.sql`).

## R0 — DONE 2026-06-28 → see `pg_policies_live_20260628.md`
Live result: `vision_*` org-scoped in prod (secure); `phone_*`+`schedule_*` `USING(true)` + anon/authenticated
SELECT grant = anonymous exposure; `sms_optout_tracking` absent from prod catalog. The query below is retained
for reproducibility.

## R0 query (read-only, run against Supabase)
Migration files ≠ live DB. The camera fix may have been applied off-main. Run (read-only):
```sql
SELECT tablename, policyname, roles, cmd, qual
FROM pg_policies
WHERE schemaname='public'
  AND tablename IN ('vision_cameras','vision_traffic','vision_visitors','vision_visits',
                    'phone_agent_config','phone_call_logs','phone_orders',
                    'schedule_staff','schedule_shifts','published_schedules','sms_optout_tracking')
ORDER BY tablename, policyname;
```
Save the output here as `pg_policies_live_YYYYMMDD.txt`. Any row with `qual='true'` and `roles` in
`{public}/{authenticated}/{anon}` is a live exposure.

## Remediation artifact
`fix_rls_wideopen.sql` (this folder) — authored, **NOT applied**. Drops wide-open, adds `TO service_role`,
provides commented org-scoped authenticated variant. Apply only after R0 + PR review + DB snapshot.

## Adversarial verification — negative test
`test_rls_cross_tenant.py` (this folder). **Execution status: AUTHORED, py_compile-clean, NOT executed in this
session** — no Postgres/psycopg on the work host; it is designed to run in CI against a throwaway Postgres
service (as the deleted `tests/e2e/test_camera_tenancy_rls.py` did) and against the live DB via `MERIDIAN_LIVE_DB`
read-only creds. It demonstrates the leak under the wide-open policy and the denial after the fix, and asserts no
permissive `USING(true)` policy remains. **Do not record this as "passing" until it has actually run in CI.**

## Status
🔴 CRITICAL OPEN (risk R-01). Readiness for CC6.1-RLS stays low until R0 confirms live state and R1/R3 land.
