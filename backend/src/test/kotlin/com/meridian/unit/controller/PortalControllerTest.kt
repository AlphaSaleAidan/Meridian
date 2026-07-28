package com.meridian.unit.controller

import com.meridian.controller.PortalController
import com.meridian.dto.GeneratePortalTokenRequest
import com.meridian.dto.PortalResolveResponse
import com.meridian.dto.PortalTokenResponse
import com.meridian.exception.NotFoundException
import com.meridian.service.portal.PortalService
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.springframework.http.HttpStatus
import java.util.UUID

class PortalControllerTest {
    private val portalService = mockk<PortalService>()
    private val portalController = PortalController(portalService)

    private val orgId = UUID.randomUUID()

    @Test
    fun `resolve returns 200 with org details`() {
        val resolved =
            PortalResolveResponse(
                orgId = orgId,
                businessName = "Maple Tandoor",
                planTier = "starter",
                portalToken = "valid-token-123",
                posProvider = null,
                onboarded = false,
            )

        every { portalService.resolveToken("valid-token-123") } returns resolved

        val response = portalController.resolve("valid-token-123")

        assertEquals(HttpStatus.OK, response.statusCode)
        assertEquals("success", response.body?.status)
        assertEquals(resolved, response.body?.data)

        verify { portalService.resolveToken("valid-token-123") }
    }

    @Test
    fun `resolve propagates NotFoundException from service`() {
        every { portalService.resolveToken("unknown-token") } throws NotFoundException("Portal link expired or invalid")

        assertThrows<NotFoundException> {
            portalController.resolve("unknown-token")
        }
    }

    @Test
    fun `generate returns 200 with portal token`() {
        val request = GeneratePortalTokenRequest(orgId)
        val tokenResponse =
            PortalTokenResponse(
                token = "new-token",
                orgId = orgId,
                portalUrl = "https://canada.meridian.tips/c/new-token",
            )

        every { portalService.generateToken(request) } returns tokenResponse

        val response = portalController.generate(request)

        assertEquals(HttpStatus.OK, response.statusCode)
        assertEquals("success", response.body?.status)
        assertEquals(tokenResponse, response.body?.data)

        verify { portalService.generateToken(request) }
    }

    @Test
    fun `generate propagates NotFoundException from service`() {
        val request = GeneratePortalTokenRequest(orgId)

        every { portalService.generateToken(request) } throws NotFoundException("Business not found")

        assertThrows<NotFoundException> {
            portalController.generate(request)
        }
    }
}
