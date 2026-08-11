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

    suspend fun save(business: Business): Business
}
