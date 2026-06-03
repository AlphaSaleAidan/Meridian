-- Fix us_leads "permission denied for table" error when sales reps add leads.
-- Root cause: 020_us_leads.sql enabled RLS and added a no-role policy, but never
-- granted table-level privileges to the authenticated role. Without GRANT, PG
-- rejects the request at the table level before RLS is even consulted.
-- Idempotent: safe to re-run.

GRANT SELECT, INSERT, UPDATE, DELETE ON public.us_leads TO authenticated;
GRANT SELECT ON public.us_leads TO anon;

-- Drop the no-role "Service role full access" policy from 020_us_leads.sql so
-- it doesn't shadow the per-role policies below (it applied to PUBLIC, which
-- includes authenticated, but had no WITH CHECK constraints worth keeping).
DROP POLICY IF EXISTS "Service role full access on us_leads" ON public.us_leads;

-- Restate the authenticated-role policies (idempotent via IF NOT EXISTS).
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='us_leads' AND policyname='Authenticated users can read US leads') THEN
    CREATE POLICY "Authenticated users can read US leads"
      ON public.us_leads FOR SELECT TO authenticated USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='us_leads' AND policyname='Authenticated users can insert US leads') THEN
    CREATE POLICY "Authenticated users can insert US leads"
      ON public.us_leads FOR INSERT TO authenticated WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='us_leads' AND policyname='Authenticated users can update US leads') THEN
    CREATE POLICY "Authenticated users can update US leads"
      ON public.us_leads FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='us_leads' AND policyname='Authenticated users can delete US leads') THEN
    CREATE POLICY "Authenticated users can delete US leads"
      ON public.us_leads FOR DELETE TO authenticated USING (true);
  END IF;
END $$;
