-- 075: close cross-tenant commission reads + make zero-policy denials explicit
--
-- Live posture findings (CC6.1 collector, 2026-08-06):
--
-- 1) commission_packages / commission_config carried USING(true) SELECT
--    policies TO authenticated — ANY logged-in user (any merchant, any rep)
--    could read the platform's full commission economics. Only the backend
--    commission_engine (service role, bypasses RLS) needs these tables; the
--    frontend never reads them directly (verified by code sweep). Drop the
--    open policies; deny-by-default takes over. When the commissions UI
--    un-pauses, add a properly scoped policy instead of restoring these.
--
-- 2) Nine tables have RLS enabled with zero policies (deny-by-default for
--    anon/authenticated; service role bypasses): checkout_sessions,
--    credit_ledger, credit_purchases, merchant_billing_terms,
--    merchant_credits, notification_prefs, phone_number_pool,
--    vision_device_tokens, voice_ledger. That posture is correct — they are
--    backend-only tables — but it is implicit: a future permissive policy or
--    grant would silently open them. Revoke the client-role grants so the
--    denial is enforced at BOTH layers (grants + RLS). No functional change:
--    with zero policies, anon/authenticated access already fails; all
--    writers use the service key.
--
-- Rollback: recreate the two policies with CREATE POLICY ... USING (true)
-- and re-GRANT as needed (not recommended).

-- 1) commission economics: drop the any-authenticated read policies
drop policy if exists "Authenticated can read commission packages" on public.commission_packages;
drop policy if exists "Authenticated can read commission config" on public.commission_config;

-- and drop the client grants for defense-in-depth
revoke all on public.commission_packages from anon, authenticated;
revoke all on public.commission_config from anon, authenticated;

-- 2) zero-policy backend tables: make the deny explicit at the grant layer
revoke all on public.checkout_sessions from anon, authenticated;
revoke all on public.credit_ledger from anon, authenticated;
revoke all on public.credit_purchases from anon, authenticated;
revoke all on public.merchant_billing_terms from anon, authenticated;
revoke all on public.merchant_credits from anon, authenticated;
revoke all on public.notification_prefs from anon, authenticated;
revoke all on public.phone_number_pool from anon, authenticated;
revoke all on public.vision_device_tokens from anon, authenticated;
revoke all on public.voice_ledger from anon, authenticated;
