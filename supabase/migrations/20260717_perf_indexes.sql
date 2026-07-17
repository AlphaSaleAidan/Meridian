-- 20260717: perf-audit indexes.
--
-- Fleet-wide (no merchant_id filter) time-window scans on these tables were
-- sequential-scanning:
--   * voice_call_endings.created_at   — call-ending telemetry rollups. The
--     existing idx_voice_call_endings_merchant is (merchant_id, created_at)
--     and can't serve a created_at-only ordering/range.
--   * career_applications.created_at  — applications inbox is listed
--     newest-first with no other indexed predicate.
--
-- Authored, NOT applied. Apply with the rest of the perf/audit-wins batch.

CREATE INDEX IF NOT EXISTS idx_voice_call_endings_created
    ON voice_call_endings(created_at);

CREATE INDEX IF NOT EXISTS idx_career_applications_created
    ON career_applications(created_at);
