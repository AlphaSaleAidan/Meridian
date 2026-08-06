package com.meridian.unit.service.portal

import com.meridian.dto.GeneratePortalTokenRequest
import com.meridian.entity.Business
import com.meridian.exception.BadRequestException
import com.meridian.exception.NotFoundException
import com.meridian.repository.BusinessRepository
import com.meridian.service.portal.PortalService
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.util.UUID

class PortalServiceTest {
    private val businessRepository = mockk<BusinessRepository>()
    private val portalService = PortalService(businessRepository, "https://canada.meridian.tips")

    private val businessId = UUID.randomUUID().toString()

    // ---- resolveToken tests ----

    @Test
    fun `resolveToken returns business details for an active business`() =
        runTest {
            val business =
                Business(
                    id = businessId,
                    name = "Maple Tandoor",
                    planTier = "growth",
                    accessToken = "valid-token-123",
                    status = "active",
                    posProvider = "square",
                    onboarded = true,
                )

            coEvery { businessRepository.findByAccessTokenAndStatus("valid-token-123", "active") } returns business

            val result = portalService.resolveToken("valid-token-123")

            assertEquals(businessId, result.businessId)
            assertEquals("Maple Tandoor", result.businessName)
            assertEquals("growth", result.planTier)
            assertEquals("valid-token-123", result.portalToken)
            assertEquals("square", result.posProvider)
            assertTrue(result.onboarded)
        }

    @Test
    fun `resolveToken defaults plan tier to starter and name to empty`() =
        runTest {
            val business = Business(id = businessId, accessToken = "valid-token-123", status = "active")

            coEvery { businessRepository.findByAccessTokenAndStatus("valid-token-123", "active") } returns business

            val result = portalService.resolveToken("valid-token-123")

            assertEquals("", result.businessName)
            assertEquals("starter", result.planTier)
        }

    @Test
    fun `resolveToken throws BadRequestException for a too-short token`() =
        runTest {
            assertThrows<BadRequestException> {
                portalService.resolveToken("short")
            }
        }

    @Test
    fun `resolveToken throws NotFoundException when no active business matches`() =
        runTest {
            coEvery { businessRepository.findByAccessTokenAndStatus("unknown-token", "active") } returns null

            assertThrows<NotFoundException> {
                portalService.resolveToken("unknown-token")
            }
        }

    // ---- generateToken tests ----

    @Test
    fun `generateToken returns existing token without saving`() =
        runTest {
            val business = Business(id = businessId, accessToken = "existing-token")

            coEvery { businessRepository.findById(businessId) } returns business

            val result = portalService.generateToken(GeneratePortalTokenRequest(businessId))

            assertEquals("existing-token", result.token)
            assertEquals(businessId, result.businessId)
            assertEquals("https://canada.meridian.tips/c/existing-token", result.portalUrl)
            coVerify(exactly = 0) { businessRepository.save(any()) }
        }

    @Test
    fun `generateToken issues and persists a new token when none exists`() =
        runTest {
            val business = Business(id = businessId)

            coEvery { businessRepository.findById(businessId) } returns business
            coEvery { businessRepository.save(any()) } answers { firstArg() }

            val result = portalService.generateToken(GeneratePortalTokenRequest(businessId))

            assertNotNull(result.token)
            assertTrue(result.token.length >= 8)
            assertEquals("https://canada.meridian.tips/c/${result.token}", result.portalUrl)
            coVerify(exactly = 1) {
                businessRepository.save(match { it.accessToken == result.token && it.tokenStatus == "pending" })
            }
        }

    @Test
    fun `generateToken throws NotFoundException when business does not exist`() =
        runTest {
            coEvery { businessRepository.findById(businessId) } returns null

            assertThrows<NotFoundException> {
                portalService.generateToken(GeneratePortalTokenRequest(businessId))
            }
        }
}
