package com.meridian.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.Table

@Entity
@Table(name = "businesses")
class Business(
    @Id
    val id: String,
    @Column(name = "name")
    var name: String? = null,
    @Column(name = "plan_tier")
    var planTier: String? = null,
    @Column(name = "access_token")
    var accessToken: String? = null,
    @Column(name = "token_status")
    var tokenStatus: String? = null,
    @Column(name = "status")
    var status: String? = null,
    @Column(name = "pos_provider")
    var posProvider: String? = null,
    @Column(name = "onboarded")
    var onboarded: Boolean = false,
)
