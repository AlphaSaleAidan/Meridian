-- POS System Tracking: selection, connection status, waitlist
-- Run this in Supabase SQL Editor

-- Add POS tracking columns to organizations table
ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS pos_system TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS pos_connection_status TEXT DEFAULT NULL
    CHECK (pos_connection_status IN ('connected', 'manual', 'pending', NULL)),
  ADD COLUMN IF NOT EXISTS pos_waitlist_email TEXT DEFAULT NULL;

-- Create a dedicated waitlist table for non-customer interest captures
CREATE TABLE IF NOT EXISTS pos_waitlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  pos_system TEXT NOT NULL,
  org_id UUID REFERENCES organizations(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  notified_at TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_pos_waitlist_system ON pos_waitlist(pos_system);
CREATE INDEX IF NOT EXISTS idx_pos_waitlist_email ON pos_waitlist(email);

-- Admin view: count merchants per POS system
CREATE OR REPLACE VIEW pos_coverage_stats AS
SELECT
  pos_system,
  COUNT(*) FILTER (WHERE pos_connection_status = 'connected') AS connected_count,
  COUNT(*) FILTER (WHERE pos_connection_status = 'manual') AS manual_count,
  COUNT(*) FILTER (WHERE pos_connection_status = 'pending') AS pending_count,
  COUNT(*) AS total_merchants
FROM organizations
WHERE pos_system IS NOT NULL
GROUP BY pos_system;

-- Waitlist counts per system
CREATE OR REPLACE VIEW pos_waitlist_stats AS
SELECT
  pos_system,
  COUNT(*) AS waitlist_count,
  COUNT(*) FILTER (WHERE notified_at IS NOT NULL) AS notified_count
FROM pos_waitlist
GROUP BY pos_system;
