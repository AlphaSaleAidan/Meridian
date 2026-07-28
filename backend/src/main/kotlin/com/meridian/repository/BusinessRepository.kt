package com.meridian.repository

import com.meridian.entity.Business
import org.springframework.data.jpa.repository.JpaRepository

interface BusinessRepository : JpaRepository<Business, String> {
    fun findByAccessTokenAndStatus(
        accessToken: String,
        status: String,
    ): Business?
}
