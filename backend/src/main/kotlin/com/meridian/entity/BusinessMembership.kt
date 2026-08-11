package com.meridian.entity

/**
 * A user's membership in one business, joined with the business name.
 *
 * Sourced from two places: `business_users` rows (staff/managers provisioned via
 * team admin) and `businesses.owner_user_id` (the account owner, who has no
 * `business_users` row).
 */
data class BusinessMembership(
    val businessId: String,
    val businessName: String? = null,
    val role: String,
    val locationId: String? = null,
)
