package com.meridian.repository

import com.meridian.entity.BusinessMembership

interface BusinessUserRepository {
    /**
     * Active staff/manager memberships for a Supabase auth user id.
     * Owner memberships are NOT here — owners live on `businesses.owner_user_id`
     * (see [BusinessRepository.findByOwnerUserId]).
     */
    suspend fun findActiveMembershipsByUserId(userId: String): List<BusinessMembership>

    /**
     * Stamp `last_login_at` and bump `login_count` on all active memberships of
     * this user. Returns the number of rows touched (0 for pure owners).
     */
    suspend fun recordLogin(userId: String): Long
}
