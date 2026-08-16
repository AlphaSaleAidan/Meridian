-- 087_vision_events.sql
-- The camera event recorder.
--
-- Everything the vision pipeline stored until now was a COUNT: people in,
-- people out, dwell seconds, queue length. Counts answer "how busy was it",
-- which is a planning question asked at the end of a week.
--
-- This table answers a different one: "what happened, and does somebody need
-- to go and deal with it". A spill is a slip claim until someone mops it. A
-- case left open is stock walking out of the door. Those are events with a
-- time and a place, not averages, and averaging them destroys the only thing
-- about them that matters.
--
-- ANONYMOUS, LIKE THE REST OF THE PIPELINE. An event records that a person
-- was at the counter on a phone for four minutes. It does not record WHICH
-- person, and there is deliberately no column that could hold one — no
-- staff_id, no face hash, no name. The identity tier is gated off
-- (CAMERA_IDENTITY_ENABLED) and this table stays outside it even when it is
-- on: "someone at the till" is enough to go and look, and it is the version
-- of this feature a merchant can run without a lawyer.

CREATE TABLE IF NOT EXISTS vision_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          TEXT NOT NULL,
    camera_id       UUID REFERENCES vision_cameras(id) ON DELETE CASCADE,
    location_id     TEXT,

    -- Controlled vocabulary, enforced here rather than in the application so a
    -- new detector cannot quietly invent a category the portal will not render.
    kind            TEXT NOT NULL CHECK (kind IN (
                        'spill',          -- liquid or debris on the floor
                        'product_loss',   -- item leaves without a sale; case left open
                        'phone_use',      -- prolonged handset use in a work zone
                        'unattended',     -- nobody on the counter while customers wait
                        'blocked_exit',   -- fire exit or aisle obstructed
                        'after_hours'     -- movement when the shop should be empty
                    )),
    severity        TEXT NOT NULL DEFAULT 'warning'
                        CHECK (severity IN ('critical', 'warning', 'info')),
    zone            TEXT,

    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Some events are instants (a bottle drops), others are durations (four
    -- minutes on a phone). Nullable rather than defaulted to zero: an unknown
    -- duration and a zero-second one are different facts.
    duration_sec    INTEGER,
    confidence      REAL,

    -- A still, never a clip. A frame is enough to decide whether to walk over
    -- and look, and storing rolling video of a workplace is a materially
    -- different privacy and retention commitment than storing a still.
    snapshot_url    TEXT,
    detail          TEXT,

    -- What a human did about it. 'new' until somebody says otherwise.
    status          TEXT NOT NULL DEFAULT 'new'
                        CHECK (status IN ('new', 'acknowledged', 'resolved', 'dismissed')),
    resolved_at     TIMESTAMPTZ,
    resolved_note   TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The feed is always "this org, newest first", usually filtered to open items.
CREATE INDEX IF NOT EXISTS vision_events_org_time_idx
    ON vision_events (org_id, detected_at DESC);

-- Partial index for the badge count, which is read on every page load of the
-- camera pillar and is almost always a small number over a large table.
CREATE INDEX IF NOT EXISTS vision_events_open_idx
    ON vision_events (org_id, detected_at DESC)
    WHERE status = 'new';

-- A detector that re-fires on the same frame must not create a second row.
-- The edge agent sends a stable key per detection window; without this, one
-- spill becomes forty spills and the feed is unusable within an hour.
ALTER TABLE vision_events
    ADD COLUMN IF NOT EXISTS dedupe_key TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS vision_events_dedupe_idx
    ON vision_events (org_id, dedupe_key)
    WHERE dedupe_key IS NOT NULL;

COMMENT ON TABLE vision_events IS
    'Discrete camera events needing a human decision (spill, product loss, phone use). Anonymous by construction: no column identifies a person.';
COMMENT ON COLUMN vision_events.snapshot_url IS
    'A single still. Deliberately not a clip — rolling workplace video is a different retention commitment.';
COMMENT ON COLUMN vision_events.dedupe_key IS
    'Stable per-detection-window key from the edge agent. Without it a re-firing detector floods the feed.';

-- ── RLS, matching the rest of the vision tables ──────────────────────────
-- Org-scoped SELECT for authenticated members; no anon policy and no anon
-- grant, so anon reads are denied outright. The backend writes with the
-- service_role key, which bypasses RLS.

ALTER TABLE vision_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS vision_events_member_isolation ON vision_events;
CREATE POLICY vision_events_member_isolation ON vision_events
    FOR SELECT TO authenticated
    USING (org_id IN (
        SELECT org_id FROM business_users WHERE user_id = auth.uid()
    ));

REVOKE ALL ON public.vision_events FROM anon;
