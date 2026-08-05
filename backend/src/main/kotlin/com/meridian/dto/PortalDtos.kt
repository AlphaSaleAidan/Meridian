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
)

data class PortalResolveResponse(
    val businessId: String,
    val businessName: String,
    val planTier: String,
    val portalToken: String,
    val posProvider: String?,
    val onboarded: Boolean,
)
