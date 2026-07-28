package com.meridian.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.Table

@Entity
@Table(name = "business_users")
class BusinessUser(
    @Id
    val id: String,
    @Column(name = "business_id")
    var businessId: String? = null,
    @Column(name = "user_id")
    var userId: String? = null,
    @Column(name = "is_active")
    var isActive: Boolean = false,
)
