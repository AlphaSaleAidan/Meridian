package com.meridian.unit.security

import com.meridian.security.MeridianRequestContextFilter
import com.meridian.security.RequestContextHolder
import com.meridian.security.SecurityConstants
import jakarta.servlet.FilterChain
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test
import org.springframework.mock.web.MockHttpServletRequest
import org.springframework.mock.web.MockHttpServletResponse

class MeridianRequestContextFilterTest {
    private val filter = MeridianRequestContextFilter()

    @Test
    fun `populates RequestContext during filter chain execution and clears afterward`() {
        val request = MockHttpServletRequest()
        val response = MockHttpServletResponse()
        val session = request.getSession(true)!!

        session.setAttribute(SecurityConstants.USER_ID_SESSION_ATTRIBUTE, "usr_456")
        session.setAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE, "pat@meridian.tips")
        session.setAttribute(SecurityConstants.BUSINESS_IDS_SESSION_ATTRIBUTE, listOf("biz_100", "biz_101"))

        var capturedUserId: String? = null
        var capturedEmail: String? = null
        var capturedBusinessIds: List<String>? = null

        val filterChain =
            FilterChain { _, _ ->
                val ctx = RequestContextHolder.get()
                capturedUserId = ctx?.userId
                capturedEmail = ctx?.userEmail
                capturedBusinessIds = ctx?.businessIds
            }

        filter.doFilter(request, response, filterChain)

        assertEquals("usr_456", capturedUserId)
        assertEquals("pat@meridian.tips", capturedEmail)
        assertEquals(listOf("biz_100", "biz_101"), capturedBusinessIds)
        assertNull(RequestContextHolder.get())
    }

    @Test
    fun `does not populate RequestContext when session is null`() {
        val request = MockHttpServletRequest()
        val response = MockHttpServletResponse()

        var ctxInsideChainPresent = false
        val filterChain =
            FilterChain { _, _ ->
                ctxInsideChainPresent = (RequestContextHolder.get() != null)
            }

        filter.doFilter(request, response, filterChain)

        assertEquals(false, ctxInsideChainPresent)
        assertNull(RequestContextHolder.get())
    }
}
