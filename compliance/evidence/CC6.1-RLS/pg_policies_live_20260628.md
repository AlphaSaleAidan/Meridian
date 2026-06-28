# R0 — LIVE `pg_policies` snapshot (read-only) — 2026-06-28

> Read-only query against live Meridian Supabase (`kbuzufjxwflrutowwnfl`) via the management API
> `database/query` endpoint. **No mutation.** This converts the file-based worst-case into ground truth and
> materially changes severities. Source: `/tmp/r0_pg_policies.py`, `/tmp/r0b.py` (token never echoed).

## Result — RLS policies on the sensitive tables (live)

| Table | Live policy | Roles | Verdict |
|---|---|---|---|
| `vision_cameras` / `vision_traffic` / `vision_visitors` / `vision_visits` | `*_member_isolation`: SELECT `USING (org_id IN (SELECT business_id FROM business_users WHERE user_id = auth.uid() AND is_active))` | `authenticated` | ✅ **SECURE in prod** — org-scoped. The camera P0 fix **was applied to live** despite the migration being absent from `main`. |
| `phone_agent_config` | `Service role full access…` `FOR ALL USING(true)` | **`public`** | 🔴 wide-open + **`anon`+`authenticated` hold SELECT grant** → readable with the public anon key. **Holds `pos_access_token`.** |
| `phone_call_logs` | same | `public` | 🔴 transcripts + caller PII |
| `phone_orders` | same | `public` | 🔴 **`anon` SELECT granted** → customer name/phone readable with public key |
| `schedule_staff` / `schedule_shifts` / `published_schedules` | `*_service` `FOR ALL USING(true)` | `public` | 🔴 `anon`/`authenticated` SELECT granted → staff roster/rates readable |
| `sms_optout_tracking` | **no policy returned; absent from `pg_class`** | — | ⚠️ table not present in prod (migration likely unapplied) — verify |

RLS enabled (`relrowsecurity=true`, `force=false`) on all phone_/schedule_ tables.
**GRANTs (verified):** `phone_agent_config`, `phone_orders`, `schedule_staff` each grant `SELECT` to **both
`anon` and `authenticated`**. Combined with the `USING(true)` policy this means the rows are readable by anyone
holding the (public, frontend-embedded) **anon key** — an anonymous exposure, not merely cross-tenant.

## Corrected severities (this supersedes the file-based scoring)
- **DOWN:** `vision_*` (biometric-sensitive) — NOT a live exposure; reclassify to **config drift** (fix not in
  `main` → regression risk on rebuild/`db push`). Action: backport the live policies into a migration on `main`
  + restore the CI denial test.
- **UP:** `phone_agent_config` / `phone_orders` / `phone_call_logs` / `schedule_*` — **anonymous read exposure
  of POS credentials + customer PII** with the public anon key. This is the single most urgent live finding.

## Remediation scope (authored, NOT applied — needs Aidan review + DB snapshot)
`fix_rls_wideopen.sql` is rescoped to the **actually-open** tables (phone_*, schedule_*): drop `USING(true)`,
add `TO service_role`, and **`REVOKE SELECT ON … FROM anon, authenticated`** (the grant is the actual exposure
vector). For `vision_*`: no change needed in prod — instead backport the live member-isolation policies to a
migration on `main`. Confirm whether `sms_optout_tracking` exists / needs the policy.
