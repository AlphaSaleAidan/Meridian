-- LingBot-Map 3D Store Mapping — extend spaces table + add processing jobs
-- Adds video-based 3D reconstruction support (no LiDAR needed)

-- Add LingBot-Map columns to existing spaces table
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS pointcloud_url TEXT;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS frame_count INTEGER;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS scan_duration_seconds INTEGER;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS model_used TEXT;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS zones_configured BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS heatmap_enabled BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE spaces ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Update scan_type to include 'lingbot' option
COMMENT ON COLUMN spaces.scan_type IS 'lidar | photogrammetry | polycam | lingbot';

-- Processing jobs for async LingBot-Map inference
CREATE TABLE IF NOT EXISTS space_processing_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id        UUID REFERENCES spaces(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'queued',  -- queued | processing | complete | failed
    progress_pct    INTEGER NOT NULL DEFAULT 0,
    frame_count     INTEGER,
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_space ON space_processing_jobs(space_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON space_processing_jobs(status);

ALTER TABLE space_processing_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on space_processing_jobs"
    ON space_processing_jobs FOR ALL
    USING (true)
    WITH CHECK (true);
