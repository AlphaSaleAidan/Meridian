# Playbook: Run Supabase Migration

## Goal
Apply a new SQL migration to the Supabase PostgreSQL database.

## Prerequisites
- Migration SQL file exists in `supabase/migrations/`
- Supabase CLI installed (`npx supabase`) or access to Supabase SQL Editor

## Option A: Supabase Dashboard (GUI)

1. Open https://supabase.com/dashboard
2. Log in (aidanpierce72@gmail.com)
3. Select the **Meridian** project
4. Go to **SQL Editor** (left sidebar)
5. Click **+ New query**
6. Paste the migration SQL content
7. Click **Run** (Cmd+Enter)
8. Verify: check **Table Editor** to confirm new tables/columns exist

## Option B: Supabase CLI (Terminal)

```bash
cd /root/Meridian
npx supabase db push
```

This applies all pending migrations from `supabase/migrations/` in order.

## Option C: Direct psql

```bash
psql "$DATABASE_URL" -f supabase/migrations/<migration_file>.sql
```

## Existing Migrations

| File | Description |
|------|-------------|
| `20260429_001_business_accounts.sql` | Business account tables |
| `20260429_002_deal_flow.sql` | Deal flow tracking |
| `20260429_003_onboarding_admin.sql` | Onboarding + admin |
| `20260501_004_vision_intelligence.sql` | Vision AI tables |
| `20260501_005_cline_agent.sql` | Cline agent config |
| `20260501_006_rls_security_fix.sql` | RLS policy fixes |
| `20260504_pos_system_tracking.sql` | POS system tracking |
| `20260505_canada_careers.sql` | Canada career listings |
| `20260505_spaces.sql` | Spaces feature |
| `20260506_career_applications_unified.sql` | Unified applications |
| `20260506_recruiters.sql` | Recruiter tables |
| `20260507_canada_leads.sql` | Canada lead tracking |
| `20260507_lingbot_map_spaces.sql` | Lingbot + map spaces |
| `20260507_phone_agent.sql` | Phone agent tables |
| `20260508_email_send_log.sql` | Email send logging |

## Naming Convention
```
YYYYMMDD_NNN_description.sql
```
Example: `20260509_001_add_payment_history.sql`

## Rollback
Supabase does not have built-in rollback. Write a reverse migration manually if needed and run it via SQL Editor.
