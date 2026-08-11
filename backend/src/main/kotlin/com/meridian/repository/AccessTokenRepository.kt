package com.meridian.repository

import com.meridian.entity.PendingBusiness
import com.meridian.entity.RedeemableToken
import java.util.UUID

interface AccessTokenRepository {
    /** The pending business behind a valid token — for the pre-signup "you're joining X" screen. */
    suspend fun findPendingBusinessByToken(token: String): PendingBusiness?

    /** The raw token row if it is still redeemable. */
    suspend fun findRedeemableToken(token: String): RedeemableToken?

    /** Marks the token redeemed by this user. Returns rows touched. */
    suspend fun markRedeemed(
        tokenId: UUID,
        userId: UUID,
    ): Long
}
