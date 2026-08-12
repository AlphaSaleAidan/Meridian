-- SR Auto Dialer — sessions, calls, callbacks, internal DNC.
-- Rep/lead-scoped (sales_reps plane) — deliberately SEPARATE from the merchant
-- phone_agent tables (phone_call_logs is merchant_id-keyed inbound order-agent
-- telemetry; do not mix the two planes).
-- Idempotent; authored only — apply via the usual hand-applied migration process
-- with a snapshot in place. NOT applied automatically.
--
-- ROLLBACK:
--   drop table if exists dialer_dnc, dialer_callbacks, dialer_calls, dialer_sessions cascade;

-- ── Tables ────────────────────────────────────────────────────────────────────

-- One row per power-dial session (rep opens the Auto Dialer tab and starts).
CREATE TABLE IF NOT EXISTS dialer_sessions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rep_id          uuid NOT NULL REFERENCES sales_reps(id),
    market          text NOT NULL DEFAULT 'canada' CHECK (market IN ('canada', 'us')),
    status          text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'ended')),
    wrap_up_seconds integer NOT NULL DEFAULT 15 CHECK (wrap_up_seconds BETWEEN 0 AND 300),
    dials           integer NOT NULL DEFAULT 0,
    connects        integer NOT NULL DEFAULT 0,
    talk_seconds    integer NOT NULL DEFAULT 0,
    started_at      timestamptz NOT NULL DEFAULT now(),
    ended_at        timestamptz,
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dialer_sessions_rep
    ON dialer_sessions (rep_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_dialer_sessions_live
    ON dialer_sessions (started_at DESC) WHERE status <> 'ended';

-- One row per dial attempt (including compliance-blocked attempts, for audit).
CREATE TABLE IF NOT EXISTS dialer_calls (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       uuid REFERENCES dialer_sessions(id),
    rep_id           uuid NOT NULL REFERENCES sales_reps(id),
    lead_id          uuid,
    lead_table       text CHECK (lead_table IN ('canada_leads', 'us_leads', 'canada_phone_leads')),
    business_name    text NOT NULL DEFAULT '',
    contact_name     text NOT NULL DEFAULT '',
    phone_e164       text NOT NULL,
    direction        text NOT NULL DEFAULT 'outbound' CHECK (direction IN ('outbound', 'inbound')),
    status           text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'dialing', 'ringing', 'connected', 'ended', 'failed', 'blocked')),
    blocked_reason   text,                 -- set when status='blocked' (dnc | calling_window | invalid_number)
    telnyx_call_id   text,
    sim              boolean NOT NULL DEFAULT false,  -- true = placed in SIM mode, no PSTN traffic
    started_at       timestamptz NOT NULL DEFAULT now(),
    answered_at      timestamptz,
    ended_at         timestamptz,
    duration_seconds integer,
    talk_seconds     integer,
    disposition      text
        CHECK (disposition IN ('meeting_booked', 'interested', 'callback', 'left_voicemail',
                               'no_answer', 'busy', 'bad_number', 'not_interested', 'dnc', 'other')),
    notes            text NOT NULL DEFAULT '',
    disposition_by   uuid,                 -- audit: admin re-disposition (NULL = the rep themselves)
    disposition_at   timestamptz,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dialer_calls_rep
    ON dialer_calls (rep_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dialer_calls_session
    ON dialer_calls (session_id);
CREATE INDEX IF NOT EXISTS idx_dialer_calls_lead
    ON dialer_calls (lead_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dialer_calls_live
    ON dialer_calls (started_at DESC) WHERE status IN ('dialing', 'ringing', 'connected');

-- Timezone-aware scheduled callbacks; due rows are fed to the top of the queue.
CREATE TABLE IF NOT EXISTS dialer_callbacks (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rep_id        uuid NOT NULL REFERENCES sales_reps(id),
    lead_id       uuid,
    lead_table    text CHECK (lead_table IN ('canada_leads', 'us_leads')),
    call_id       uuid REFERENCES dialer_calls(id),
    phone_e164    text NOT NULL,
    business_name text NOT NULL DEFAULT '',
    contact_name  text NOT NULL DEFAULT '',
    due_at        timestamptz NOT NULL,
    timezone      text NOT NULL DEFAULT '',
    note          text NOT NULL DEFAULT '',
    status        text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'cancelled')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dialer_callbacks_due
    ON dialer_callbacks (rep_id, due_at) WHERE status = 'pending';

-- Internal do-not-call list. Checked (hard block) at dial time; the 'dnc'
-- disposition writes here instantly. Necessary-not-sufficient: national DNCL
-- subscription is a separate org-level obligation before cold-list calling.
CREATE TABLE IF NOT EXISTS dialer_dnc (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_e164      text NOT NULL UNIQUE,
    market          text NOT NULL DEFAULT 'canada' CHECK (market IN ('canada', 'us')),
    reason          text NOT NULL DEFAULT '',
    added_by_rep_id uuid,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- ── RLS ───────────────────────────────────────────────────────────────────────
-- Writes: service_role only (all mutations go through the backend API).
-- Reads: scoped SELECT for authenticated — self, downline (managers), admin —
-- required so Supabase Realtime (admin live board) can deliver rows under RLS.
-- dialer_dnc is backend-only in both directions.
-- Uses the SECURITY DEFINER helpers from 20260716_sales_hierarchy.sql:
-- current_rep_id(), current_rep_role(), current_rep_path(), rep_path_for(uuid).

ALTER TABLE dialer_sessions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE dialer_calls     ENABLE ROW LEVEL SECURITY;
ALTER TABLE dialer_callbacks ENABLE ROW LEVEL SECURITY;
ALTER TABLE dialer_dnc       ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['dialer_sessions', 'dialer_calls', 'dialer_callbacks', 'dialer_dnc'] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE tablename = t AND policyname = t || '_service_all'
        ) THEN
            EXECUTE format(
                'CREATE POLICY %I ON %I FOR ALL TO service_role USING (true) WITH CHECK (true)',
                t || '_service_all', t
            );
        END IF;
    END LOOP;
END $$;

DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['dialer_sessions', 'dialer_calls', 'dialer_callbacks'] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE tablename = t AND policyname = t || '_scoped_read'
        ) THEN
            EXECUTE format(
                'CREATE POLICY %I ON %I FOR SELECT TO authenticated USING ('
                '    current_rep_role() = ''admin'''
                '    OR rep_id = current_rep_id()'
                '    OR ('
                '        current_rep_role() IS NOT NULL'
                '        AND current_rep_role() <> ''sales_rep'''
                '        AND current_rep_path() IS NOT NULL'
                '        AND rep_path_for(rep_id) LIKE current_rep_path() || ''.%%'''
                '    )'
                ')',
                t || '_scoped_read', t
            );
        END IF;
    END LOOP;
END $$;

-- ── Realtime (admin live board) ───────────────────────────────────────────────

ALTER TABLE dialer_sessions REPLICA IDENTITY FULL;
ALTER TABLE dialer_calls    REPLICA IDENTITY FULL;

DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE dialer_sessions;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE dialer_calls;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
