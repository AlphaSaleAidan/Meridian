-- voice_call_endings dedupe: _record_call_ending was select-then-insert, so
-- concurrent Vapi end-of-call-report retries could double-insert the same
-- call. Enforce one row per vapi_call_id at the DB layer; the writer now
-- pairs this with a resolution=ignore-duplicates upsert (vapi_webhook.py).
-- Rows with NULL vapi_call_id (payloads missing a call id) stay unconstrained.
-- Idempotent; authored only — apply via the usual migration process.

CREATE UNIQUE INDEX IF NOT EXISTS voice_call_endings_vapi_call_id_uniq
    ON voice_call_endings (vapi_call_id)
    WHERE vapi_call_id IS NOT NULL;
