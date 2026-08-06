package com.meridian.unit.security

import com.meridian.exception.UnauthorizedException
import com.meridian.security.RequestContext
import com.meridian.security.RequestContextArgumentResolver
import com.meridian.security.SecurityConstants
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.springframework.core.MethodParameter
import org.springframework.mock.web.MockHttpServletRequest
import org.springframework.web.context.request.ServletWebRequest

class RequestContextArgumentResolverTest {
    private val resolver = RequestContextArgumentResolver()

    @Suppress("unused", "UNUSED_PARAMETER")
    private class Handlers {
        fun required(context: RequestContext) {}

        fun optional(context: RequestContext?) {}

        fun other(name: String) {}
    }

    private fun param(
        methodName: String,
        type: Class<*>,
    ): MethodParameter = MethodParameter(Handlers::class.java.getDeclaredMethod(methodName, type), 0)

    @Test
    fun `supports RequestContext parameters only`() {
        assertTrue(resolver.supportsParameter(param("required", RequestContext::class.java)))
        assertFalse(resolver.supportsParameter(param("other", String::class.java)))
    }

    @Test
    fun `resolves context from session attributes`() {
        val request = MockHttpServletRequest()
        val session = request.getSession(true)!!
        session.setAttribute(SecurityConstants.USER_ID_SESSION_ATTRIBUTE, "usr_123")
        session.setAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE, "dev@meridian.tips")
        session.setAttribute(SecurityConstants.BUSINESS_IDS_SESSION_ATTRIBUTE, listOf("biz_1"))

        val resolved =
            resolver.resolveArgument(param("required", RequestContext::class.java), null, ServletWebRequest(request), null)

        assertEquals(RequestContext("usr_123", "dev@meridian.tips", listOf("biz_1")), resolved)
    }

    @Test
    fun `throws UnauthorizedException when no session and parameter is required`() {
        val request = MockHttpServletRequest()

        assertThrows<UnauthorizedException> {
            resolver.resolveArgument(param("required", RequestContext::class.java), null, ServletWebRequest(request), null)
        }
    }

    @Test
    fun `returns null when no session and parameter is nullable`() {
        val request = MockHttpServletRequest()

        val resolved =
            resolver.resolveArgument(param("optional", RequestContext::class.java), null, ServletWebRequest(request), null)

        assertNull(resolved)
    }

    @Test
    fun `throws when session lacks a complete identity`() {
        val request = MockHttpServletRequest()
        request.getSession(true)!!.setAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE, "dev@meridian.tips")

        assertThrows<UnauthorizedException> {
            resolver.resolveArgument(param("required", RequestContext::class.java), null, ServletWebRequest(request), null)
        }
    }
}
