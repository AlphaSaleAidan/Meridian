package com.meridian.dto

data class GeneratePortalTokenRequest(
    val orgId: String,
)

data class PortalTokenResponse(
    val token: String,
    val orgId: String,
    val portalUrl: String,
)

data class PortalResolveResponse(
    val orgId: String,
    val businessName: String,
    val planTier: String,
    val portalToken: String,
    val posProvider: String?,
    val onboarded: Boolean,
)
