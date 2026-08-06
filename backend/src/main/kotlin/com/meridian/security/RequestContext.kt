package com.meridian.security

import jakarta.servlet.http.HttpSession

/**
 * Immutable request context carrying user identity and multi-tenant business access scoping.
 */
data class RequestContext(
    val userId: String,
    val userEmail: String,
    val businessIds: List<String> = emptyList(),
) {
    companion object {
        /**
         * Builds a [RequestContext] from the session attributes written at login, or null
         * when the session carries no complete identity. Single source of truth for the
         * session-attribute mapping, shared by [MeridianRequestContextFilter] and
         * [RequestContextArgumentResolver].
         */
        fun fromSession(session: HttpSession): RequestContext? {
            val userId = session.getAttribute(SecurityConstants.USER_ID_SESSION_ATTRIBUTE) as? String ?: return null
            val userEmail = session.getAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE) as? String ?: return null

            @Suppress("UNCHECKED_CAST")
            val businessIds = session.getAttribute(SecurityConstants.BUSINESS_IDS_SESSION_ATTRIBUTE) as? List<String> ?: emptyList()

            return RequestContext(userId = userId, userEmail = userEmail, businessIds = businessIds)
        }
    }
}
