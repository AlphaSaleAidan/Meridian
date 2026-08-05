package com.meridian.repository

import com.meridian.entity.Business

interface BusinessRepository {
    suspend fun findById(id: String): Business?

    suspend fun findByAccessTokenAndStatus(
        accessToken: String,
        status: String,
    ): Business?

    suspend fun save(business: Business): Business
}
