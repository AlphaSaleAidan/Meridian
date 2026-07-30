package com.meridian.service.auth

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty

/** Wire shape of the Supabase GoTrue token response (only the fields we consume). */
@JsonIgnoreProperties(ignoreUnknown = true)
data class SupabaseTokenResponse(
    @param:JsonProperty("access_token") val accessToken: String? = null,
    val user: SupabaseUser? = null,
) {
    @JsonIgnoreProperties(ignoreUnknown = true)
    data class SupabaseUser(
        val id: String? = null,
    )
}

/** Wire shape of GoTrue error bodies — the message field varies by endpoint/version. */
@JsonIgnoreProperties(ignoreUnknown = true)
data class SupabaseErrorResponse(
    val msg: String? = null,
    @param:JsonProperty("error_description") val errorDescription: String? = null,
    val error: String? = null,
) {
    fun firstMessage(): String? = msg ?: errorDescription ?: error
}
