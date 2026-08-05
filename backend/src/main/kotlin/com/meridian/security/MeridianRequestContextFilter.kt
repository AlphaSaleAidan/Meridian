package com.meridian.security

import jakarta.servlet.FilterChain
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.springframework.stereotype.Component
import org.springframework.web.filter.OncePerRequestFilter

/**
 * Servlet filter that extracts user identity and business access scoping from the active HTTP Session,
 * populating [RequestContextHolder] for the duration of the request.
 *
 * Guarantees context cleanup in a `finally` block to prevent cross-request thread contamination.
 */
@Component
class MeridianRequestContextFilter : OncePerRequestFilter() {
    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        filterChain: FilterChain,
    ) {
        val session = request.getSession(false)
        if (session != null) {
            val userId = session.getAttribute(SecurityConstants.USER_ID_SESSION_ATTRIBUTE) as? String
            val userEmail = session.getAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE) as? String

            @Suppress("UNCHECKED_CAST")
            val businessIds = session.getAttribute(SecurityConstants.BUSINESS_IDS_SESSION_ATTRIBUTE) as? List<String> ?: emptyList()

            // TODO: Hook up database resolution for userId and businessIds when user management/access tables are created
            if (userId != null && userEmail != null) {
                val context =
                    RequestContext(
                        userId = userId,
                        userEmail = userEmail,
                        businessIds = businessIds,
                    )
                RequestContextHolder.set(context)
            }
        }

        try {
            filterChain.doFilter(request, response)
        } finally {
            RequestContextHolder.clear()
        }
    }
}
