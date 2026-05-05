-- 3D Space Management — scan storage, model metadata, zone mapping
-- Supports LiDAR, photogrammetry, and Polycam embed scans

CREATE TABLE IF NOT EXISTS spaces (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      TEXT NOT NULL,
    scan_type   TEXT NOT NULL DEFAULT 'lidar',       -- lidar | photogrammetry | polycam
    device_model TEXT,                                -- e.g. "iPhone 15 Pro"
    file_format TEXT NOT NULL DEFAULT 'usdz',        -- usdz | glb | obj | ply
    file_size_bytes BIGINT,
    source_url  TEXT,                                 -- Polycam embed URL or Supabase Storage path
    model_url   TEXT,                                 -- processed 3D model URL (GLB)
    thumbnail_url TEXT,                               -- preview image
    status      TEXT NOT NULL DEFAULT 'uploaded',     -- uploaded | processing | ready | failed
    metadata    JSONB DEFAULT '{}',                   -- arbitrary scan metadata
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_spaces_org ON spaces(org_id);
CREATE INDEX IF NOT EXISTS idx_spaces_status ON spaces(status);

-- Zone mapping — links detected zones to a space
CREATE TABLE IF NOT EXISTS space_zones (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id    UUID NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    zone_id     TEXT NOT NULL,
    label       TEXT NOT NULL,
    position_x  REAL NOT NULL DEFAULT 0,
    position_y  REAL NOT NULL DEFAULT 0,
    position_z  REAL NOT NULL DEFAULT 0,
    radius      REAL NOT NULL DEFAULT 1,
    category    TEXT NOT NULL DEFAULT 'general',     -- general | counter | entrance | display | shelf
    traffic     INTEGER DEFAULT 0,
    dwell_minutes REAL DEFAULT 0,
    conversion_pct REAL DEFAULT 0,
    revenue_per_sqft REAL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_space_zones_space ON space_zones(space_id);

-- RLS policies
ALTER TABLE spaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE space_zones ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on spaces"
    ON spaces FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on space_zones"
    ON space_zones FOR ALL
    USING (true)
    WITH CHECK (true);

-- View: space summary per org
CREATE OR REPLACE VIEW space_summary AS
SELECT
    org_id,
    COUNT(*) AS total_spaces,
    COUNT(*) FILTER (WHERE status = 'ready') AS ready_spaces,
    COUNT(*) FILTER (WHERE status = 'processing') AS processing_spaces,
    MAX(created_at) AS latest_scan
FROM spaces
GROUP BY org_id;
