-- Vision cameras table for Meridian Vision Intelligence
CREATE TABLE IF NOT EXISTS vision_cameras (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  location_id UUID,
  name TEXT NOT NULL,
  rtsp_url TEXT NOT NULL,
  zone_config JSONB DEFAULT '{}',
  compliance_mode TEXT NOT NULL DEFAULT 'anonymous' CHECK (compliance_mode IN ('anonymous', 'opt_in_identity', 'disabled')),
  active_hours JSONB DEFAULT '{"start": "07:00", "end": "22:00"}',
  edge_device_id TEXT,
  status TEXT NOT NULL DEFAULT 'offline',
  last_heartbeat TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vision_cameras_org ON vision_cameras(org_id);

-- Vision traffic metrics
CREATE TABLE IF NOT EXISTS vision_traffic (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  camera_id UUID REFERENCES vision_cameras(id) ON DELETE SET NULL,
  location_id UUID,
  bucket TIMESTAMPTZ NOT NULL,
  entries INT DEFAULT 0,
  exits INT DEFAULT 0,
  occupancy_avg REAL DEFAULT 0,
  occupancy_peak INT DEFAULT 0,
  queue_length_avg REAL DEFAULT 0,
  queue_wait_avg_sec REAL DEFAULT 0,
  conversion_rate REAL DEFAULT 0,
  demographic_breakdown JSONB DEFAULT '{}',
  depth_zone_occupancy JSONB,
  avg_person_distance REAL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (org_id, camera_id, bucket)
);

CREATE INDEX idx_vision_traffic_org_bucket ON vision_traffic(org_id, bucket DESC);

-- Vision visitors (opt-in identity mode only)
CREATE TABLE IF NOT EXISTS vision_visitors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  embedding_hash TEXT,
  first_seen TIMESTAMPTZ,
  last_seen TIMESTAMPTZ,
  visit_count INT DEFAULT 1,
  demographic JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vision_visitors_org ON vision_visitors(org_id);

-- Vision visits (individual visit records)
CREATE TABLE IF NOT EXISTS vision_visits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  camera_id UUID REFERENCES vision_cameras(id) ON DELETE SET NULL,
  visitor_id UUID REFERENCES vision_visitors(id) ON DELETE SET NULL,
  entered_at TIMESTAMPTZ NOT NULL,
  exited_at TIMESTAMPTZ,
  dwell_seconds INT,
  zones_visited TEXT[] DEFAULT '{}',
  converted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vision_visits_org ON vision_visits(org_id, entered_at DESC);

-- RLS policies
ALTER TABLE vision_cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE vision_traffic ENABLE ROW LEVEL SECURITY;
ALTER TABLE vision_visitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE vision_visits ENABLE ROW LEVEL SECURITY;

-- Service role can do everything
CREATE POLICY "Service role full access on vision_cameras" ON vision_cameras FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on vision_traffic" ON vision_traffic FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on vision_visitors" ON vision_visitors FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on vision_visits" ON vision_visits FOR ALL USING (true) WITH CHECK (true);
