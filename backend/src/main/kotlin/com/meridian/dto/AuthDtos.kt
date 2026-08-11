package com.meridian.dto

data class SignupRequest(
    val email: String,
    val password: String,
)

data class LoginRequest(
    val email: String,
    val password: String,
)

data class SessionInfoResponse(
    val id: String,
    val email: String,
    val displayName: String? = null,
    val role: String,
    val orgId: String? = null,
    val locationId: String? = null,
    val isVerified: Boolean = false,
    val isAdmin: Boolean = false,
    val isSalesRep: Boolean = false,
    val businesses: List<SessionBusinessResponse> = emptyList(),
)

data class SessionBusinessResponse(
    val businessId: String,
    val businessName: String? = null,
    val role: String,
    val locationId: String? = null,
)
