package com.meridian.dto

import java.util.UUID

data class GeneratePortalTokenRequest(
    val orgId: UUID,
)

data class PortalTokenResponse(
    val token: String,
    val orgId: UUID,
    val portalUrl: String,
)

data class PortalResolveResponse(
    val orgId: UUID,
    val businessName: String,
    val planTier: String,
    val portalToken: String,
    val posProvider: String?,
    val onboarded: Boolean,
)
