package com.meridian.dto

data class SignupRequest(
    val email: String,
    val password: String,
)

data class LoginRequest(
    val email: String,
    val password: String,
)

data class ForgotPasswordRequest(
    val email: String,
)

data class ResetPasswordRequest(
    /** Recovery access token from the Supabase email link's URL fragment. */
    val accessToken: String,
    val newPassword: String,
)

data class ChangePasswordRequest(
    /** Verified via a fresh Supabase password grant — also sidesteps stored-token expiry. */
    val currentPassword: String,
    val newPassword: String,
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
