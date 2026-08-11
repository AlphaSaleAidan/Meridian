package com.meridian.dto

data class SignupRequest(
    val email: String,
    val password: String,
    val displayName: String? = null,
    /** Self-serve signup: name of the business to create. Ignored when accessToken is set. */
    val businessName: String? = null,
    /** Invite flow: rep-issued token binding this signup to a pre-created business. */
    val accessToken: String? = null,
)

data class SignupResponse(
    /** Business created (self-serve) or bound (invite); null when neither applies. */
    val businessId: String? = null,
)

data class PendingBusinessResponse(
    val businessId: String,
    val businessName: String? = null,
    val ownerName: String? = null,
    val email: String? = null,
    val businessType: String? = null,
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
