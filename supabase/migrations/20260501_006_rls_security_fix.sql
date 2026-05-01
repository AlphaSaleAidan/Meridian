-- Fix: Enable RLS on 4 public tables flagged by Supabase Security Advisor
-- Tables: admin_users, benchmark_snapshots, industry_aggregates, data_export_logs
-- Priority: CRITICAL — these were publicly readable without access control

-- ═══════════════════════════════════════════════════════════
-- 1. admin_users — MOST CRITICAL
--    Only admins should read/write their own row
-- ═══════════════════════════════════════════════════════════
ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins can view own record"
    ON public.admin_users FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Service role full access on admin_users"
    ON public.admin_users FOR ALL
    USING (auth.role() = 'service_role');

-- ═══════════════════════════════════════════════════════════
-- 2. benchmark_snapshots — org-scoped via benchmark_profile
--    Merchants can only see their own snapshots
-- ═══════════════════════════════════════════════════════════
ALTER TABLE public.benchmark_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own benchmark snapshots"
    ON public.benchmark_snapshots FOR SELECT
    USING (
        benchmark_profile_id IN (
            SELECT id FROM benchmark_profiles
            WHERE org_id = get_user_org_id()
        )
    );

CREATE POLICY "Service role full access on benchmark_snapshots"
    ON public.benchmark_snapshots FOR ALL
    USING (auth.role() = 'service_role');

-- ═══════════════════════════════════════════════════════════
-- 3. industry_aggregates — anonymized data, read-only for authenticated
--    This is the sellable asset — no merchant-specific data
-- ═══════════════════════════════════════════════════════════
ALTER TABLE public.industry_aggregates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read industry aggregates"
    ON public.industry_aggregates FOR SELECT
    USING (auth.role() = 'authenticated');

CREATE POLICY "Service role full access on industry_aggregates"
    ON public.industry_aggregates FOR ALL
    USING (auth.role() = 'service_role');

-- ═══════════════════════════════════════════════════════════
-- 4. data_export_logs — admin/service only
--    Export tracking should not be public
-- ═══════════════════════════════════════════════════════════
ALTER TABLE public.data_export_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Only admins can view export logs"
    ON public.data_export_logs FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM admin_users WHERE user_id = auth.uid())
    );

CREATE POLICY "Service role full access on data_export_logs"
    ON public.data_export_logs FOR ALL
    USING (auth.role() = 'service_role');
