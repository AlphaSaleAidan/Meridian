package com.meridian.repository

/**
 * Actor ids stamped into created_by / modified_by audit columns.
 *
 * SYSTEM is the uuid-shaped sentinel (ends in 37) used when no acting user is
 * available — seeds, migrations, and unattributed upserts. It is also the DB
 * DEFAULT for created_by (supabase/migrations/20260811_audit_metadata.sql), so
 * keep the two in sync.
 */
object AuditActor {
    const val SYSTEM = "00000000-0000-0000-0000-000000000037"
}
