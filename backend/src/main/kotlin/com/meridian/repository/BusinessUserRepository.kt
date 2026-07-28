package com.meridian.repository

import com.meridian.entity.BusinessUser
import org.springframework.data.jpa.repository.JpaRepository

interface BusinessUserRepository : JpaRepository<BusinessUser, String> {
    fun existsByBusinessIdAndUserIdAndIsActiveTrue(
        businessId: String,
        userId: String,
    ): Boolean
}
