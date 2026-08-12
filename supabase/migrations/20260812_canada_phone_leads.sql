-- Canada phone-lead dialing pool + booking appointments for the SR auto dialer.
--
-- WHY A SEPARATE TABLE: canada_leads is the LIVE sales pipeline (late-stage
-- deals: proposal_shown / customer_walkthrough / customer_checkout). Cold-call
-- prospects with raw numbers must NOT land there — it would pollute every stage
-- count and trip the RLS/regression tripwires. The dialer works this pool; a
-- deliberate one-click "promote" is the ONLY bridge into canada_leads.
--
-- Idempotent; authored only — apply by hand with a snapshot. NOT auto-applied.
-- Does NOT alter canada_leads.
--
-- ROLLBACK:
--   drop table if exists dialer_appointments, canada_phone_leads cascade;

-- ── Dialing pool ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS canada_phone_leads (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name    text NOT NULL DEFAULT '',
    contact_name     text NOT NULL DEFAULT '',
    phone_e164       text NOT NULL,
    contact_email    text NOT NULL DEFAULT '',
    city             text NOT NULL DEFAULT '',
    province         text NOT NULL DEFAULT '',
    vertical         text NOT NULL DEFAULT '',
    -- The "has ___ POS" enrichment shown on every call card.
    pos_system       text NOT NULL DEFAULT 'unknown',   -- square|clover|toast|lightspeed|none|unknown|<free text>
    pos_source       text NOT NULL DEFAULT '',          -- how we know (import|rep|scrape)
    website          text NOT NULL DEFAULT '',
    est_monthly_value integer NOT NULL DEFAULT 0,        -- cents; indicative, not a quote
    notes            text NOT NULL DEFAULT '',
    -- Lifecycle in the dialing pool (separate from canada_leads.stage).
    status           text NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'attempting', 'contacted', 'callback', 'booked',
                          'converted', 'not_interested', 'bad_number', 'dnc', 'dead')),
    attempts         integer NOT NULL DEFAULT 0,
    last_attempt_at  timestamptz,
    last_disposition text,
    -- Recapture clock: when this lead should re-surface in the queue.
    -- NULL = ready now; future = held (cooldown / scheduled callback).
    next_action_at   timestamptz,
    rep_id           uuid REFERENCES sales_reps(id),     -- owner/assignee (NULL = shared pool)
    source           text NOT NULL DEFAULT '',           -- capture batch / list name
    -- Set when promoted into the real pipeline (the one-click bridge).
    converted_lead_id uuid,                              -- -> canada_leads.id (no FK: cross-domain, soft link)
    converted_at     timestamptz,
    created_by_rep_id uuid,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cpl_rep_status
    ON canada_phone_leads (rep_id, status);
-- Recapture queue: ready leads (next_action_at null or due) ordered by urgency.
CREATE INDEX IF NOT EXISTS idx_cpl_next_action
    ON canada_phone_leads (rep_id, next_action_at)
    WHERE status IN ('new', 'attempting', 'contacted', 'callback');
CREATE INDEX IF NOT EXISTS idx_cpl_phone
    ON canada_phone_leads (phone_e164);
CREATE INDEX IF NOT EXISTS idx_cpl_source
    ON canada_phone_leads (source);

-- ── Booking calendar ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dialer_appointments (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_lead_id  uuid REFERENCES canada_phone_leads(id) ON DELETE CASCADE,
    rep_id         uuid NOT NULL REFERENCES sales_reps(id),
    lead_id        uuid,                                 -- canada_leads.id once promoted (soft link)
    business_name  text NOT NULL DEFAULT '',
    contact_name   text NOT NULL DEFAULT '',
    phone_e164     text NOT NULL DEFAULT '',
    scheduled_at   timestamptz NOT NULL,
    duration_min   integer NOT NULL DEFAULT 30 CHECK (duration_min BETWEEN 5 AND 240),
    timezone       text NOT NULL DEFAULT '',
    title          text NOT NULL DEFAULT 'Demo',
    notes          text NOT NULL DEFAULT '',
    status         text NOT NULL DEFAULT 'booked'
        CHECK (status IN ('booked', 'completed', 'cancelled', 'no_show')),
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dialer_appts_rep_when
    ON dialer_appointments (rep_id, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_dialer_appts_lead
    ON dialer_appointments (phone_lead_id);

-- ── RLS ───────────────────────────────────────────────────────────────────────
-- Writes: service_role only (all mutations go through the backend API).
-- Reads: scoped SELECT for authenticated — self / downline (managers) / admin —
-- so Realtime and direct reads honour the hierarchy. Same idiom as canada_leads
-- + 20260716_sales_hierarchy helpers (current_rep_id/role/path, rep_path_for).

ALTER TABLE canada_phone_leads  ENABLE ROW LEVEL SECURITY;
ALTER TABLE dialer_appointments ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['canada_phone_leads', 'dialer_appointments'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = t AND policyname = t || '_service_all') THEN
            EXECUTE format(
                'CREATE POLICY %I ON %I FOR ALL TO service_role USING (true) WITH CHECK (true)',
                t || '_service_all', t);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = t AND policyname = t || '_scoped_read') THEN
            EXECUTE format(
                'CREATE POLICY %I ON %I FOR SELECT TO authenticated USING ('
                '    current_rep_role() = ''admin'''
                '    OR rep_id = current_rep_id()'
                '    OR rep_id IS NULL'
                '    OR ('
                '        current_rep_role() IS NOT NULL'
                '        AND current_rep_role() <> ''sales_rep'''
                '        AND current_rep_path() IS NOT NULL'
                '        AND rep_path_for(rep_id) LIKE current_rep_path() || ''.%%'''
                '    )'
                ')',
                t || '_scoped_read', t);
        END IF;
    END LOOP;
END $$;

-- ── Realtime (queue + calendar live updates) ──────────────────────────────────
ALTER TABLE canada_phone_leads  REPLICA IDENTITY FULL;
ALTER TABLE dialer_appointments REPLICA IDENTITY FULL;

DO $$
BEGIN ALTER PUBLICATION supabase_realtime ADD TABLE canada_phone_leads;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN ALTER PUBLICATION supabase_realtime ADD TABLE dialer_appointments;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
