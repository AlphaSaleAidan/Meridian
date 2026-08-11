package com.meridian.repository

import com.meridian.entity.Business
import java.util.UUID

interface BusinessRepository {
    suspend fun findById(id: String): Business?

    suspend fun findByAccessTokenAndStatus(
        accessToken: String,
        status: String,
    ): Business?

    /** Businesses owned by this Supabase auth user (`businesses.owner_user_id`). */
    suspend fun findByOwnerUserId(ownerUserId: UUID): List<Business>

    /**
     * Creates an active business owned by this user (self-serve signup).
     * Returns the new business id. Mirrors `create_business_for_user`.
     */
    suspend fun insertOwnedBusiness(
        id: String,
        name: String,
        ownerName: String?,
        email: String,
        ownerUserId: UUID,
    ): String

    /**
     * Binds a pre-created business to its owner at invite redemption:
     * token_status 'redeemed', status 'active', activated_at now. Returns rows
     * touched. Mirrors the `redeem_access_token` business update.
     */
    suspend fun activateForOwner(
        businessId: String,
        ownerUserId: UUID,
    ): Long

    suspend fun save(business: Business): Business
}
