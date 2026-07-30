package com.meridian.service.auth

/**
 * Tenancy guard for org-scoped endpoints (port of require_org_access).
 */
interface OrgAccessService {
    /**
     * True when the caller may act on [orgId]: their email is on the internal
     * admin allowlist, or the session user owns the org, or they are an
     * active member. Callers decide how to reject a false result (401 when
     * [userId] is null, 403 otherwise).
     */
    suspend fun hasOrgAccess(
        userId: String?,
        email: String?,
        orgId: String,
    ): Boolean
}
