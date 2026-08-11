package com.meridian.service.auth

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty

/**
 * Typed projections of Supabase Auth REST responses (never `Map<String, Any>`).
 * Only the fields the backend consumes are declared; the rest are ignored.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
data class SupabaseTokenResponse(
    @param:JsonProperty("access_token") val accessToken: String,
    val user: SupabaseUser,
)

@JsonIgnoreProperties(ignoreUnknown = true)
data class SupabaseUser(
    val id: String,
    val email: String? = null,
    @param:JsonProperty("email_confirmed_at") val emailConfirmedAt: String? = null,
    @param:JsonProperty("user_metadata") val userMetadata: SupabaseUserMetadata? = null,
    /**
     * Anti-enumeration marker: with email confirmations ON, GoTrue answers a
     * signup for an ALREADY-REGISTERED email with 200 and a fabricated user
     * whose identities list is EMPTY. Absent on login responses.
     */
    val identities: List<SupabaseIdentity>? = null,
)

@JsonIgnoreProperties(ignoreUnknown = true)
data class SupabaseIdentity(
    val id: String? = null,
)

/**
 * SECURITY NOTE: `user_metadata` is writable by the end user via Supabase's
 * `updateUser` — treat these fields as cosmetic only. Roles and business access
 * are derived from the `businesses`/`business_users`/`admin_users` tables, never
 * from this metadata.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
data class SupabaseUserMetadata(
    @param:JsonProperty("display_name") val displayName: String? = null,
    @param:JsonProperty("full_name") val fullName: String? = null,
)

/** Result of a successful credential login: the token plus who logged in. */
data class SupabaseSession(
    val accessToken: String,
    val user: SupabaseUser,
)

/**
 * GoTrue's /signup response varies: with email confirmation ON the user object
 * is the top level (id/email inline); with autoconfirm it nests under `user`.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
data class SupabaseSignupResponse(
    val id: String? = null,
    val email: String? = null,
    val identities: List<SupabaseIdentity>? = null,
    val user: SupabaseUser? = null,
) {
    fun toUser(): SupabaseUser? = user ?: id?.let { SupabaseUser(id = it, email = email, identities = identities) }
}
