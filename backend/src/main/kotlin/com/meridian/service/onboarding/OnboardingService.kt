package com.meridian.service.onboarding

import com.meridian.entity.PendingBusiness
import java.util.UUID

interface OnboardingService {
    /**
     * The business behind a valid invite token, for the pre-signup screen.
     * Throws NotFoundException when the token is unknown, redeemed or expired.
     */
    suspend fun validateToken(token: String): PendingBusiness

    /**
     * Redeems an invite token for a freshly signed-up user: marks the token
     * redeemed, binds `owner_user_id` and activates the business, records the
     * onboarding step — one transaction (port of `redeem_access_token`).
     * Returns the bound business id.
     */
    suspend fun redeemForUser(
        token: String,
        userId: UUID,
    ): String

    /**
     * Self-serve signup: creates an active business owned by the user and
     * records the onboarding step — one transaction (port of
     * `create_business_for_user`). Returns the new business id.
     */
    suspend fun createBusinessForOwner(
        userId: UUID,
        businessName: String,
        ownerName: String?,
        email: String,
    ): String
}
