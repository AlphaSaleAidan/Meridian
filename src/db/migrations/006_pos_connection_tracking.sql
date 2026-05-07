-- ============================================================
-- Migration 006: POS Connection Tracking
-- ============================================================
-- IMPORTANT: Flagged for Aidan review before running in production.
-- This migration adds POS system tracking to leads and merchants.
--
-- Credential storage: pos_credentials is JSONB but values MUST be
-- encrypted before INSERT. Use POS_CREDENTIAL_ENCRYPTION_KEY env var
-- with AES-256-GCM. Never store plaintext API keys.
-- ============================================================

-- Leads: track which POS system was selected and connection status
ALTER TABLE leads ADD COLUMN IF NOT EXISTS pos_system_id TEXT;

ALTER TABLE leads ADD COLUMN IF NOT EXISTS pos_connection_status TEXT
  DEFAULT 'not_connected'
  CHECK (pos_connection_status IN (
    'not_connected',
    'pending_oauth',
    'connected',
    'manual_setup',
    'waitlisted',
    'error'
  ));

ALTER TABLE leads ADD COLUMN IF NOT EXISTS pos_credentials JSONB;

-- Merchants: same tracking for active accounts
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS pos_system_id TEXT;

ALTER TABLE merchants ADD COLUMN IF NOT EXISTS pos_connection_status TEXT
  DEFAULT 'not_connected'
  CHECK (pos_connection_status IN (
    'not_connected',
    'pending_oauth',
    'connected',
    'manual_setup',
    'waitlisted',
    'error'
  ));

-- RLS: credentials column should only be readable by the merchant's own org
-- (Existing RLS policies on leads/merchants already enforce org-level access)

-- Index for dashboard queries filtering by POS type
CREATE INDEX IF NOT EXISTS idx_leads_pos_system ON leads (pos_system_id) WHERE pos_system_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_merchants_pos_system ON merchants (pos_system_id) WHERE pos_system_id IS NOT NULL;
