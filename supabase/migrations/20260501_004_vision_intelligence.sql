-- ADR-011: In-Store Vision Intelligence
-- 4 tables for camera management, visitor tracking, visit records, and traffic metrics

-- 1. Camera registration and health
CREATE TABLE IF NOT EXISTS vision_cameras (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    location_id     UUID REFERENCES locations(id) ON DELETE SET NULL,
    name            TEXT NOT NULL,
    rtsp_url        TEXT NOT NULL,
    zone_config     JSONB NOT NULL DEFAULT '{}',
    compliance_mode TEXT NOT NULL DEFAULT 'anonymous'
        CHECK (compliance_mode IN ('anonymous', 'opt_in_identity', 'disabled')),
    active_hours    JSONB NOT NULL DEFAULT '{"start": "07:00", "end": "22:00"}',
    status          TEXT NOT NULL DEFAULT 'offline'
        CHECK (status IN ('online', 'offline', 'error')),
    last_heartbeat  TIMESTAMPTZ,
    edge_device_id  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vision_cameras_org ON vision_cameras(org_id);
CREATE INDEX idx_vision_cameras_status ON vision_cameras(org_id, status);

-- 2. Anonymized visitor sessions (opt_in_identity mode only)
CREATE TABLE IF NOT EXISTS vision_visitors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    embedding_hash  TEXT NOT NULL,
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
    visit_count     INTEGER NOT NULL DEFAULT 1,
    demographic     JSONB NOT NULL DEFAULT '{}',
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '90 days'),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vision_visitors_org ON vision_visitors(org_id);
CREATE INDEX idx_vision_visitors_hash ON vision_visitors(org_id, embedding_hash);
CREATE INDEX idx_vision_visitors_expires ON vision_visitors(expires_at);

-- 3. Individual visit records
CREATE TABLE IF NOT EXISTS vision_visits (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    visitor_id      UUID REFERENCES vision_visitors(id) ON DELETE SET NULL,
    camera_id       UUID NOT NULL REFERENCES vision_cameras(id) ON DELETE CASCADE,
    entered_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    exited_at       TIMESTAMPTZ,
    dwell_seconds   INTEGER,
    zones_visited   TEXT[] NOT NULL DEFAULT '{}',
    converted       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vision_visits_org ON vision_visits(org_id);
CREATE INDEX idx_vision_visits_camera ON vision_visits(camera_id, entered_at DESC);
CREATE INDEX idx_vision_visits_entered ON vision_visits(org_id, entered_at DESC);

-- 4. Aggregated traffic metrics (15-minute buckets)
CREATE TABLE IF NOT EXISTS vision_traffic (
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    location_id         UUID REFERENCES locations(id) ON DELETE SET NULL,
    camera_id           UUID NOT NULL REFERENCES vision_cameras(id) ON DELETE CASCADE,
    bucket              TIMESTAMPTZ NOT NULL,
    entries             INTEGER NOT NULL DEFAULT 0,
    exits               INTEGER NOT NULL DEFAULT 0,
    occupancy_avg       FLOAT NOT NULL DEFAULT 0,
    occupancy_peak      INTEGER NOT NULL DEFAULT 0,
    queue_length_avg    FLOAT NOT NULL DEFAULT 0,
    queue_wait_avg_sec  FLOAT NOT NULL DEFAULT 0,
    conversion_rate     FLOAT NOT NULL DEFAULT 0,
    demographic_breakdown JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (org_id, camera_id, bucket)
);

CREATE INDEX idx_vision_traffic_bucket ON vision_traffic(org_id, bucket DESC);
CREATE INDEX idx_vision_traffic_location ON vision_traffic(org_id, location_id, bucket DESC);

-- RLS policies
ALTER TABLE vision_cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE vision_visitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE vision_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE vision_traffic ENABLE ROW LEVEL SECURITY;

CREATE POLICY vision_cameras_org_isolation ON vision_cameras
    USING (org_id = auth.uid());
CREATE POLICY vision_visitors_org_isolation ON vision_visitors
    USING (org_id = auth.uid());
CREATE POLICY vision_visits_org_isolation ON vision_visits
    USING (org_id = auth.uid());
CREATE POLICY vision_traffic_org_isolation ON vision_traffic
    USING (org_id = auth.uid());

-- Auto-delete expired visitor records (run via pg_cron or scheduled function)
CREATE OR REPLACE FUNCTION cleanup_expired_visitors()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM vision_visits
    WHERE visitor_id IN (
        SELECT id FROM vision_visitors WHERE expires_at < now()
    );

    WITH deleted AS (
        DELETE FROM vision_visitors
        WHERE expires_at < now()
        RETURNING id
    )
    SELECT count(*) INTO deleted_count FROM deleted;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
