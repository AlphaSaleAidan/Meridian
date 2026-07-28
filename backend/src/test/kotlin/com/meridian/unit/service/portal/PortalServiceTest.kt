package com.meridian.unit.service.portal

import com.meridian.dto.GeneratePortalTokenRequest
import com.meridian.entity.Business
import com.meridian.exception.BadRequestException
import com.meridian.exception.NotFoundException
import com.meridian.repository.BusinessRepository
import com.meridian.service.portal.PortalService
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.util.Optional
import java.util.UUID

class PortalServiceTest {
    private val businessRepository = mockk<BusinessRepository>()
    private val portalService = PortalService(businessRepository, "https://canada.meridian.tips")

    private val orgId = UUID.randomUUID().toString()

    // ---- resolveToken tests ----

    @Test
    fun `resolveToken returns org details for an active business`() {
        val business =
            Business(
                id = orgId,
                name = "Maple Tandoor",
                planTier = "growth",
                accessToken = "valid-token-123",
                status = "active",
                posProvider = "square",
                onboarded = true,
            )

        every { businessRepository.findByAccessTokenAndStatus("valid-token-123", "active") } returns business

        val result = portalService.resolveToken("valid-token-123")

        assertEquals(orgId, result.orgId)
        assertEquals("Maple Tandoor", result.businessName)
        assertEquals("growth", result.planTier)
        assertEquals("valid-token-123", result.portalToken)
        assertEquals("square", result.posProvider)
        assertTrue(result.onboarded)
    }

    @Test
    fun `resolveToken defaults plan tier to starter and name to empty`() {
        val business = Business(id = orgId, accessToken = "valid-token-123", status = "active")

        every { businessRepository.findByAccessTokenAndStatus("valid-token-123", "active") } returns business

        val result = portalService.resolveToken("valid-token-123")

        assertEquals("", result.businessName)
        assertEquals("starter", result.planTier)
    }

    @Test
    fun `resolveToken throws BadRequestException for a too-short token`() {
        assertThrows<BadRequestException> {
            portalService.resolveToken("short")
        }
    }

    @Test
    fun `resolveToken throws NotFoundException when no active business matches`() {
        every { businessRepository.findByAccessTokenAndStatus("unknown-token", "active") } returns null

        assertThrows<NotFoundException> {
            portalService.resolveToken("unknown-token")
        }
    }

    // ---- generateToken tests ----

    @Test
    fun `generateToken returns existing token without saving`() {
        val business = Business(id = orgId, accessToken = "existing-token")

        every { businessRepository.findById(orgId) } returns Optional.of(business)

        val result = portalService.generateToken(GeneratePortalTokenRequest(orgId))

        assertEquals("existing-token", result.token)
        assertEquals(orgId, result.orgId)
        assertEquals("https://canada.meridian.tips/c/existing-token", result.portalUrl)
        verify(exactly = 0) { businessRepository.save(any()) }
    }

    @Test
    fun `generateToken issues and persists a new token when none exists`() {
        val business = Business(id = orgId)

        every { businessRepository.findById(orgId) } returns Optional.of(business)
        every { businessRepository.save(business) } returns business

        val result = portalService.generateToken(GeneratePortalTokenRequest(orgId))

        assertNotNull(result.token)
        assertTrue(result.token.length >= 8)
        assertEquals(result.token, business.accessToken)
        assertEquals("pending", business.tokenStatus)
        assertEquals("https://canada.meridian.tips/c/${result.token}", result.portalUrl)
        verify(exactly = 1) { businessRepository.save(business) }
    }

    @Test
    fun `generateToken throws NotFoundException when business does not exist`() {
        every { businessRepository.findById(orgId) } returns Optional.empty()

        assertThrows<NotFoundException> {
            portalService.generateToken(GeneratePortalTokenRequest(orgId))
        }
    }
}
