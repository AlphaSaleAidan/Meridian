package com.meridian.entity

import java.util.UUID

/** An `access_tokens` row that is still redeemable (not redeemed, not expired). */
data class RedeemableToken(
    val id: UUID,
    val businessId: String,
)
