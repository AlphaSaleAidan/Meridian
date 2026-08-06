package com.meridian.unit.controller

import com.meridian.controller.PortalController
import com.meridian.dto.GeneratePortalTokenRequest
import com.meridian.dto.PortalResolveResponse
import com.meridian.dto.PortalTokenResponse
import com.meridian.exception.NotFoundException
import com.meridian.service.portal.PortalService
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.springframework.http.HttpStatus
import java.util.UUID

class PortalControllerTest {
    private val portalService = mockk<PortalService>()
    private val portalController = PortalController(portalService)

    private val businessId = UUID.randomUUID().toString()

    @Test
    fun `resolve returns 200 with org details`(): Unit =
        runTest {
            val resolved =
                PortalResolveResponse(
                    businessId = businessId,
                    businessName = "Maple Tandoor",
                    planTier = "starter",
                    portalToken = "valid-token-123",
                    posProvider = null,
                    onboarded = false,
                )

            coEvery { portalService.resolveToken("valid-token-123") } returns resolved

            val response = portalController.resolve("valid-token-123")

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("success", response.body?.status)
            assertEquals(resolved, response.body?.data)

            coVerify { portalService.resolveToken("valid-token-123") }
        }

    @Test
    fun `resolve propagates NotFoundException from service`(): Unit =
        runTest {
            coEvery { portalService.resolveToken("unknown-token") } throws NotFoundException("Portal link expired or invalid")

            assertThrows<NotFoundException> {
                portalController.resolve("unknown-token")
            }
        }

    @Test
    fun `generate returns 200 with portal token`(): Unit =
        runTest {
            val request = GeneratePortalTokenRequest(businessId)
            val tokenResponse =
                PortalTokenResponse(
                    token = "new-token",
                    businessId = businessId,
                    portalUrl = "https://canada.meridian.tips/c/new-token",
                )

            coEvery { portalService.generateToken(request) } returns tokenResponse

            val response = portalController.generate(request)

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("success", response.body?.status)
            assertEquals(tokenResponse, response.body?.data)

            coVerify { portalService.generateToken(request) }
        }

    @Test
    fun `generate propagates NotFoundException from service`(): Unit =
        runTest {
            val request = GeneratePortalTokenRequest(businessId)

            coEvery { portalService.generateToken(request) } throws NotFoundException("Business not found")

            assertThrows<NotFoundException> {
                portalController.generate(request)
            }
        }
}
