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

## Secondary RLS findings — also verified live (most file-based findings were OVERSTATED)
| Item (file-based concern) | Live truth | Verdict |
|---|---|---|
| `get_user_org_id()` undefined | **defined in prod** (`pg_proc`) | ✅ not an issue |
| `transactions` exposed | RLS on; `SELECT USING (org_id = get_user_org_id())` | ✅ org-scoped |
| `subscriptions` | RLS on; `org_id = get_user_org_id()` (+ owner role for writes) | ✅ org-scoped |
| `pos_connections` (POS tokens) | RLS on, 3 policies, **no anon grant** | ✅ protected |
| `access_tokens` / `login_attempts` (file said "no RLS") | RLS on with policies (`created_by = auth.uid()` / `id = auth.uid()`) | ✅ has RLS |
| `square_/clover_/toast_transactions` | **not present in prod** (phase-2 cutover unapplied) | n/a |
| `cline_*` / `merchant_health` | RLS on, org-scoped (the `business_id = auth.uid()` quirk is a *functionality* edge, not exposure) | 🟡 low |

**Defense-in-depth observation (currently safe, fragile):** many tables (`transactions`, `subscriptions`,
`cline_*`, `merchant_health`, `access_tokens`, `login_attempts`) grant `SELECT` to **`anon`**. This is safe
*only* because their RLS is org-scoped (anon's `auth.uid()`/`get_user_org_id()` is null → 0 rows). Recommend
revoking `anon SELECT` where anon access isn't needed, so security doesn't rest solely on every policy staying
org-scoped. Lower priority than the phone_/schedule_ fix.

**Net: the only confirmed LIVE RLS exposures are `phone_*` and `schedule_*`.** Financial + PII + POS-token
tables are properly isolated in prod.

## Remediation scope (authored, NOT applied — needs Aidan review + DB snapshot)
`fix_rls_wideopen.sql` is rescoped to the **actually-open** tables (phone_*, schedule_*): drop `USING(true)`,
add `TO service_role`, and **`REVOKE SELECT ON … FROM anon, authenticated`** (the grant is the actual exposure
vector). For `vision_*`: no change needed in prod — instead backport the live member-isolation policies to a
migration on `main`. Confirm whether `sms_optout_tracking` exists / needs the policy.
