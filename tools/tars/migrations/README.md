# TARS Migration Reference

Migration SQL files live in `/root/Meridian/supabase/migrations/`. This directory is a quick-reference index for TARS playbooks.

## Applied Migrations

| File | Date | Description |
|------|------|-------------|
| `20260429_001_business_accounts.sql` | 2026-04-29 | Business account tables |
| `20260429_002_deal_flow.sql` | 2026-04-29 | Deal flow tracking |
| `20260429_003_onboarding_admin.sql` | 2026-04-29 | Onboarding + admin panels |
| `20260501_004_vision_intelligence.sql` | 2026-05-01 | Vision AI tables (ADR-011) |
| `20260501_005_cline_agent.sql` | 2026-05-01 | Cline agent config |
| `20260501_006_rls_security_fix.sql` | 2026-05-01 | RLS policy hardening |
| `20260504_pos_system_tracking.sql` | 2026-05-04 | POS system tracking |
| `20260505_canada_careers.sql` | 2026-05-05 | Canada career listings |
| `20260505_spaces.sql` | 2026-05-05 | Spaces feature |
| `20260506_career_applications_unified.sql` | 2026-05-06 | Unified job applications |
| `20260506_recruiters.sql` | 2026-05-06 | Recruiter management |
| `20260507_canada_leads.sql` | 2026-05-07 | Canada lead capture |
| `20260507_lingbot_map_spaces.sql` | 2026-05-07 | Lingbot + map spaces |
| `20260507_phone_agent.sql` | 2026-05-07 | Phone agent tables |
| `20260508_email_send_log.sql` | 2026-05-08 | Email send logging |

## Creating New Migrations

Naming convention: `YYYYMMDD_NNN_short_description.sql`

Place new files in `supabase/migrations/` and run via:
- Supabase CLI: `npx supabase db push`
- SQL Editor: paste into Supabase dashboard
- psql: `psql "$DATABASE_URL" -f supabase/migrations/<file>.sql`

See `tools/tars/playbooks/run_supabase_migration.md` for the full playbook.
