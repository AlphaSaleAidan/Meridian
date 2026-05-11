-- Add credentials_encrypted column for API-key-based POS systems (Toast, TouchBistro, etc.)
-- OAuth systems (Square, Clover) continue using access_token_encrypted / refresh_token_encrypted.
-- This column stores a JSONB of {field_name: encrypted_value} for each credential field.

ALTER TABLE pos_connections
    ADD COLUMN IF NOT EXISTS credentials_encrypted JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS last_error TEXT;

-- Index for scheduler lookups (find connections due for sync)
CREATE INDEX IF NOT EXISTS idx_pos_connections_sync_due
    ON pos_connections (status, historical_import_complete, last_sync_at)
    WHERE status = 'connected' AND historical_import_complete = TRUE;

COMMENT ON COLUMN pos_connections.credentials_encrypted IS
    'Encrypted API credentials for non-OAuth POS systems. Each value is AES-256-GCM encrypted.';
