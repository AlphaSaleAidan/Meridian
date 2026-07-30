package com.meridian.repository

/**
 * Org-membership lookups backing the tenancy layer.
 *
 * Hand-rolled db layer (no Spring Data JPA): implementations own their SQL so
 * the exact queries the tenancy checks run are explicit and reviewable.
 */
interface OrgMembershipRepository {
    /** True when businesses.owner_user_id of [orgId] is [userId]. */
    fun isOwner(
        orgId: String,
        userId: String,
    ): Boolean

    /** True when an active business_users row links [userId] to [orgId]. */
    fun isActiveMember(
        orgId: String,
        userId: String,
    ): Boolean
}
