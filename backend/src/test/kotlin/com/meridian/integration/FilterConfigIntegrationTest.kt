package com.meridian.integration

import com.meridian.dto.ApiResponse
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
import org.springframework.boot.test.context.TestConfiguration
import org.springframework.boot.web.servlet.FilterRegistrationBean
import org.springframework.context.annotation.Bean
import org.springframework.http.ResponseEntity
import org.springframework.mock.web.MockHttpServletRequest
import org.springframework.mock.web.MockHttpServletResponse
import org.springframework.test.context.ActiveProfiles
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@SpringBootTest
@ActiveProfiles("test")
@Tag("integration")
class FilterConfigIntegrationTest : PostgresIntegrationTest() {
    @Autowired
    private lateinit var meridianRequestContextFilter: MeridianRequestContextFilter

    @TestConfiguration
    class TestFilterConfig {
        @Bean
        fun testScopedFilterRegistration(filter: MeridianRequestContextFilter): FilterRegistrationBean<MeridianRequestContextFilter> {
            val registration = FilterRegistrationBean(filter)
            registration.addUrlPatterns("/api/test/*")
            return registration
        }

        @RestController
        @RequestMapping("/api/test")
        class TestDummyController {
            @GetMapping("/context")
            fun getContext(): ResponseEntity<ApiResponse<Any>> {
                val ctx = RequestContextHolder.get()
                return if (ctx != null) {
                    ResponseEntity.ok(ApiResponse.success(data = ctx))
                } else {
                    ResponseEntity.ok(ApiResponse.error(code = 400, message = "No context"))
                }
            }
        }
    }

    @Test
    fun `context loads and MeridianRequestContextFilter is registered`() {
        assertNotNull(meridianRequestContextFilter)
    }

    @Test
    fun `filter loads RequestContext on mapped url pattern with active session`() {
        val request = MockHttpServletRequest("GET", "/api/test/context")
        val response = MockHttpServletResponse()
        val session = request.getSession(true)!!

        session.setAttribute(SecurityConstants.USER_ID_SESSION_ATTRIBUTE, "usr_dummy_777")
        session.setAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE, "dummy@meridian.tips")
        session.setAttribute(SecurityConstants.BUSINESS_IDS_SESSION_ATTRIBUTE, listOf("biz_x", "biz_y"))

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

        assertEquals("usr_dummy_777", capturedUserId)
        assertEquals("dummy@meridian.tips", capturedEmail)
        assertEquals(listOf("biz_x", "biz_y"), capturedBusinessIds)

        // Guarantee zero thread context contamination after request finishes
        assertNull(RequestContextHolder.get())
    }

    @Test
    fun `filter returns no context when session is unauthenticated`() {
        val request = MockHttpServletRequest("GET", "/api/test/context")
        val response = MockHttpServletResponse()

        var ctxInsideChainPresent = false
        val filterChain =
            FilterChain { _, _ ->
                ctxInsideChainPresent = (RequestContextHolder.get() != null)
            }

        meridianRequestContextFilter.doFilter(request, response, filterChain)

        assertEquals(false, ctxInsideChainPresent)
        assertNull(RequestContextHolder.get())
    }
}
