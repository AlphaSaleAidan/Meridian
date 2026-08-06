package com.meridian.dto

import com.fasterxml.jackson.annotation.JsonAlias

data class GeneratePortalTokenRequest(
    @JsonAlias("orgId")
    val businessId: String,
)

data class PortalTokenResponse(
    val token: String,
    val businessId: String,
    val portalUrl: String,
) {
    /** Transitional duplicate of [businessId] so consumers still reading `orgId` keep working. */
    @Deprecated("Read businessId instead; orgId is dropped once the SPA migrates.", ReplaceWith("businessId"))
    val orgId: String get() = businessId
}

data class PortalResolveResponse(
    val businessId: String,
    val businessName: String,
    val planTier: String,
    val portalToken: String,
    val posProvider: String?,
    val onboarded: Boolean,
) {
    /** Transitional duplicate of [businessId] so consumers still reading `orgId` keep working. */
    @Deprecated("Read businessId instead; orgId is dropped once the SPA migrates.", ReplaceWith("businessId"))
    val orgId: String get() = businessId
}
