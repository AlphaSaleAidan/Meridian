package com.meridian.security

import com.meridian.exception.UnauthorizedException
import jakarta.servlet.http.HttpServletRequest
import org.springframework.core.MethodParameter
import org.springframework.web.bind.support.WebDataBinderFactory
import org.springframework.web.context.request.NativeWebRequest
import org.springframework.web.method.support.HandlerMethodArgumentResolver
import org.springframework.web.method.support.ModelAndViewContainer

/**
 * Resolves [RequestContext] controller parameters straight from the HTTP session.
 *
 * This is the suspension-safe way to consume the request context: the value is materialized
 * once, before the handler coroutine starts, so it survives the thread hops of suspend
 * handlers — a ThreadLocal read via [RequestContextHolder] does not (the coroutine resumes
 * on a different thread after the first suspension point).
 *
 * Declare the parameter nullable (`RequestContext?`) to make the context optional; non-null
 * parameters throw [UnauthorizedException] when the session carries no complete identity.
 */
class RequestContextArgumentResolver : HandlerMethodArgumentResolver {
    override fun supportsParameter(parameter: MethodParameter): Boolean = parameter.parameterType == RequestContext::class.java

    override fun resolveArgument(
        parameter: MethodParameter,
        mavContainer: ModelAndViewContainer?,
        webRequest: NativeWebRequest,
        binderFactory: WebDataBinderFactory?,
    ): Any? {
        val session = webRequest.getNativeRequest(HttpServletRequest::class.java)?.getSession(false)
        val context = session?.let { RequestContext.fromSession(it) }
        if (context == null && !parameter.isOptional) {
            throw UnauthorizedException("Not authenticated")
        }
        return context
    }
}
