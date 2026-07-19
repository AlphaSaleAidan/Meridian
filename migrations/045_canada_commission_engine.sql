-- ============================================================
-- 045: CANADA COMMISSION ENGINE (milestone-based, integer cents)
-- ============================================================
-- Replaces the dead percentage commission system for the Canada
-- portal. Context: the `commissions` table has 0 rows ever;
-- billing.py:498 + stripe_checkout.py:142 insert columns that do
-- not exist (type/amount_cents/...) and fail silently; the
-- calculate_commission() RPC has no callers. This migration is
-- ADDITIVE ONLY — it does not touch the legacy tables and nothing
-- writes these tables until the engine is reviewed and wired.
--
-- Formula (official Rep Commission One-Pager):
--   Total commission splits across 4 milestones in fixed 57-unit
--   weights M0=13, M1=28, M2=10, M3=6.
--   payout(package, milestone) = unit_value(package) x weight.
--   Unit values live in commission_packages — a new tier is a row
--   insert, not a code change.
--
-- All money columns are INTEGER CENTS.
-- ============================================================

-- ============================================================
-- PACKAGE CATALOG (config table — source of unit values)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.commission_packages (
    package_key        text PRIMARY KEY,
    display_name       text NOT NULL DEFAULT '',
    list_monthly_cents integer NOT NULL CHECK (list_monthly_cents > 0),
    unit_value_cents   integer NOT NULL CHECK (unit_value_cents > 0),
    currency           text NOT NULL DEFAULT 'CAD',
    -- OPEN QUESTION #1 (default true, flagged for Aidan/Enoch):
    -- the $200 minimum-price package is its own SKU (anchor), NOT a
    -- discounted Starter. The engine reads this flag together with
    -- commission_config.min_price_is_anchor.
    is_anchor          boolean NOT NULL DEFAULT false,
    active             boolean NOT NULL DEFAULT true,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

INSERT INTO public.commission_packages
    (package_key, display_name, list_monthly_cents, unit_value_cents, is_anchor)
VALUES
    ('minimum', 'Minimum price', 20000,  600, true),   -- $200/mo, unit $6.00  -> total $342.00
    ('starter', 'Starter',       25000,  750, false),  -- $250/mo, unit $7.50  -> total $427.50
    ('middle',  'Middle',        39900, 1375, false),  -- $399/mo, unit $13.75 -> total $783.75
    ('higher',  'Higher',        68900, 2000, false)   -- $689/mo, unit $20.00 -> total $1,140.00
ON CONFLICT (package_key) DO NOTHING;

-- ============================================================
-- ENGINE CONFIG (flags + settlement calendar — all PARAMETERIZED
-- open questions with defaults; each needs Aidan/Enoch sign-off)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.commission_config (
    key         text PRIMARY KEY,
    value       jsonb NOT NULL,
    description text NOT NULL DEFAULT '',
    updated_at  timestamptz NOT NULL DEFAULT now()
);

INSERT INTO public.commission_config (key, value, description) VALUES
    ('min_price_is_anchor', 'true',
     'OPEN #1: $200 is its own SKU with its own schedule, NOT a discounted Starter. Discount rule applies only to non-anchor slider prices. false = treat $200 as Starter minus $50.'),
    ('m0_floor_zero', 'true',
     'OPEN #2: M0 floors at $0, never negative.'),
    ('currency', '"CAD"',
     'OPEN #3: commission currency.'),
    ('retro_upsell_commission', 'false',
     'OPEN #4: post-close upsells generate no commission. true = pay 0.50 x monthly delta once.'),
    ('settlement_months', '[1, 4, 7, 10]',
     'FLAGGED for Aidan sign-off: quarterly settlement months (M1/M2/M3 pay dates).'),
    ('settlement_day_rule', '"first_friday"',
     'FLAGGED for Aidan sign-off: settlement day within each settlement month.'),
    ('m0_min_gap_days', '7',
     'M0 pays the first Friday at least this many days after close (full payroll week between). Tuesday close -> next-week Friday.')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- MILESTONE LEDGER (one row per account x milestone)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.commission_milestones (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id     uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    rep_id         uuid NOT NULL REFERENCES public.sales_reps(id) ON DELETE CASCADE,
    assignment_id  uuid REFERENCES public.rep_client_assignments(id) ON DELETE SET NULL,
    package_key    text NOT NULL REFERENCES public.commission_packages(package_key),

    milestone      text NOT NULL CHECK (milestone IN ('M0', 'M1', 'M2', 'M3')),
    -- NOTE: if commission_config.m0_floor_zero is ever flipped to false
    -- (negative M0 allowed), this CHECK must be dropped in the same change.
    amount_cents   integer NOT NULL CHECK (amount_cents >= 0),
    currency       text NOT NULL DEFAULT 'CAD',

    earned_at      date,           -- close date (M0) / months 4-9-12 of activity
    payable_on     date,           -- M0: Friday after a full payroll week;
                                   -- M1-M3: next quarterly settlement after earn
    paid_at        timestamptz,

    -- 'pending' = scheduled, earn date in the future
    -- 'earned'  = earned, awaiting payout
    -- 'paid'    = disbursed (never clawed back)
    -- 'halted'  = account cancelled before the earn date
    status         text NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'earned', 'paid', 'halted')),

    -- classification (independent-contractor, lump-sum, outcome-based),
    -- negotiated price snapshot, adjustment audit trail
    metadata       jsonb NOT NULL DEFAULT '{}',

    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),

    -- Idempotency: double-scheduling an account is a no-op
    -- (engine upserts with ON CONFLICT DO NOTHING on this key).
    CONSTRAINT uq_commission_milestones_account_ms UNIQUE (account_id, milestone)
);

CREATE INDEX IF NOT EXISTS idx_commission_ms_rep      ON public.commission_milestones(rep_id);
CREATE INDEX IF NOT EXISTS idx_commission_ms_account  ON public.commission_milestones(account_id);
CREATE INDEX IF NOT EXISTS idx_commission_ms_status   ON public.commission_milestones(status);
CREATE INDEX IF NOT EXISTS idx_commission_ms_payable  ON public.commission_milestones(payable_on);

-- ============================================================
-- RLS — service_role writes ONLY; reps read ONLY their own rows.
--
-- Write path: the backend uses the service role key (bypasses
-- RLS). No INSERT/UPDATE/DELETE policies exist for authenticated,
-- so user-JWT writes are denied outright.
--
-- Read path: same email-join isolation as canada_leads
-- (supabase/migrations/20260628_canada_leads_rep_isolation.sql) —
-- auth.uid() != sales_reps.id (reps are provisioned by the
-- backend, not auth signup), so auth.email() is the join key.
-- ============================================================
ALTER TABLE public.commission_milestones ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Reps can read own commission milestones" ON public.commission_milestones;
CREATE POLICY "Reps can read own commission milestones"
  ON public.commission_milestones FOR SELECT
  TO authenticated
  USING (
    rep_id IN (
      SELECT id FROM public.sales_reps WHERE email = auth.email()
    )
  );

-- Package catalog + config: read-only reference data for any
-- authenticated portal user; writes via service role only.
ALTER TABLE public.commission_packages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated can read commission packages" ON public.commission_packages;
CREATE POLICY "Authenticated can read commission packages"
  ON public.commission_packages FOR SELECT
  TO authenticated
  USING (true);

ALTER TABLE public.commission_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated can read commission config" ON public.commission_config;
CREATE POLICY "Authenticated can read commission config"
  ON public.commission_config FOR SELECT
  TO authenticated
  USING (true);
