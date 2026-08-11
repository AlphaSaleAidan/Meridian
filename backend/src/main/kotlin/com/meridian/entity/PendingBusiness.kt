package com.meridian.entity

/**
 * The business behind a valid (unredeemed, unexpired) invite token —
 * `access_tokens` joined to `businesses`, mirroring the `validate_access_token`
 * SQL function the SPA calls today.
 */
data class PendingBusiness(
    val businessId: String,
    val businessName: String? = null,
    val ownerName: String? = null,
    val email: String? = null,
    val businessType: String? = null,
)
