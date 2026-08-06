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
 *
 * IMPORTANT: the ThreadLocal behind [RequestContextHolder] is only visible to a suspend handler
 * until its first suspension point — after that the coroutine resumes on a different thread and
 * reads null. Suspend controllers must take [RequestContext] as a handler parameter (resolved by
 * [RequestContextArgumentResolver]) instead of reading the holder after any I/O. This filter's
 * registration is disabled in [com.meridian.config.FilterConfig] until a non-suspend consumer exists.
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
            // TODO: Hook up database resolution for userId and businessIds when user management/access tables are created
            RequestContext.fromSession(session)?.let { RequestContextHolder.set(it) }
        }

        try {
            filterChain.doFilter(request, response)
        } finally {
            RequestContextHolder.clear()
        }
    }
}
