package com.meridian.service.user

import java.io.Serializable

/**
 * Fully resolved identity for a logged-in user, stored in the JDBC session at
 * login and served by `GET /api/auth/me`.
 *
 * [Serializable] because spring-session-jdbc persists session attributes with
 * JDK serialization.
 *
 * Roles and access are table-derived (`businesses.owner_user_id`,
 * `business_users`, `admin_users`, `sales_reps`) — never from Supabase
 * `user_metadata`, which end users can edit themselves.
 */
data class UserIdentity(
    val userId: String,
    val email: String,
    val displayName: String? = null,
    /** Role in the primary business ("owner"/"manager"/"staff"); "staff" when the user has no business. */
    val role: String,
    /** Primary business id (first owned, else first membership), null when none. */
    val orgId: String? = null,
    val locationId: String? = null,
    val isVerified: Boolean = false,
    val isAdmin: Boolean = false,
    val isSalesRep: Boolean = false,
    val businesses: List<UserBusiness> = emptyList(),
) : Serializable

data class UserBusiness(
    val businessId: String,
    val businessName: String? = null,
    val role: String,
    val locationId: String? = null,
) : Serializable
