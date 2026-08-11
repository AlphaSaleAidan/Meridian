package com.meridian.service.user

import java.util.UUID

interface UserIdentityService {
    /**
     * Resolves the full [UserIdentity] for a Supabase auth user: owned businesses
     * (`businesses.owner_user_id`), active staff/manager memberships
     * (`business_users`), platform-admin grant (`admin_users`) and active
     * sales-rep status (`sales_reps`).
     */
    suspend fun resolveIdentity(
        userId: UUID,
        email: String,
        displayName: String?,
        isVerified: Boolean,
    ): UserIdentity

    /** Stamps login bookkeeping (`last_login_at`, `login_count`) on the user's active memberships. */
    suspend fun recordLogin(userId: UUID)
}
