package com.meridian.integration

import com.meridian.security.MeridianRequestContextFilter
import com.meridian.security.RequestContextHolder
import com.meridian.security.SecurityConstants
import com.meridian.support.PostgresIntegrationTest
import jakarta.servlet.FilterChain
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.mock.web.MockHttpServletRequest
import org.springframework.mock.web.MockHttpServletResponse
import org.springframework.test.context.ActiveProfiles

@SpringBootTest
@ActiveProfiles("test")
@Tag("integration")
class RequestContextIntegrationTest : PostgresIntegrationTest() {
    @Autowired
    private lateinit var meridianRequestContextFilter: MeridianRequestContextFilter

    @Test
    fun `context loads and MeridianRequestContextFilter bean is registered`() {
        assertNotNull(meridianRequestContextFilter)
    }

    @Test
    fun `session populates request context during HTTP request in Spring context`() {
        val request = MockHttpServletRequest()
        val response = MockHttpServletResponse()
        val session = request.getSession(true)!!

        session.setAttribute(SecurityConstants.USER_ID_SESSION_ATTRIBUTE, "usr_integration_999")
        session.setAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE, "integration@meridian.tips")
        session.setAttribute(SecurityConstants.BUSINESS_IDS_SESSION_ATTRIBUTE, listOf("biz_alpha", "biz_beta"))

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

        meridianRequestContextFilter.doFilter(request, response, filterChain)

        assertEquals("usr_integration_999", capturedUserId)
        assertEquals("integration@meridian.tips", capturedEmail)
        assertEquals(listOf("biz_alpha", "biz_beta"), capturedBusinessIds)
        assertNull(RequestContextHolder.get())
    }
}
