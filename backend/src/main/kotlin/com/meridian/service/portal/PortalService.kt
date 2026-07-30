package com.meridian.service.portal

import com.meridian.dto.GeneratePortalTokenRequest
import com.meridian.dto.PortalResolveResponse
import com.meridian.dto.PortalTokenResponse
import com.meridian.exception.BadRequestException
import com.meridian.exception.NotFoundException
import com.meridian.repository.BusinessRepository
import com.meridian.repository.schema.Business
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.data.repository.findByIdOrNull
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.security.SecureRandom
import java.util.Base64

/**
 * Portal token service — secure per-customer portal URLs.
 *
 * Each customer gets a unique portal token (e.g. /c/8f2a9b3c4d) stored in
 * businesses.access_token. This gives them an exclusive URL for their dashboard.
 */
@Service
class PortalService(
    private val businessRepository: BusinessRepository,
    @Value("\${meridian.portal.base-url}") private val portalBaseUrl: String,
) {
    private val log = LoggerFactory.getLogger(PortalService::class.java)
    private val secureRandom = SecureRandom()

    @Transactional(readOnly = true)
    fun resolveToken(token: String): PortalResolveResponse {
        if (token.length < MIN_TOKEN_LENGTH) {
            throw BadRequestException("Invalid token")
        }

        val business =
            businessRepository.findByAccessTokenAndStatus(token, ACTIVE_STATUS)
                ?: throw NotFoundException("Portal link expired or invalid")

        return PortalResolveResponse(
            orgId = business.id,
            businessName = business.name.orEmpty(),
            planTier = business.planTier ?: DEFAULT_PLAN_TIER,
            portalToken = token,
            posProvider = business.posProvider,
            onboarded = business.onboarded,
        )
    }

    @Transactional
    fun generateToken(request: GeneratePortalTokenRequest): PortalTokenResponse {
        val business =
            businessRepository.findByIdOrNull(request.orgId)
                ?: throw NotFoundException("Business not found")

        val token = business.accessToken ?: issueToken(business)

        return PortalTokenResponse(
            token = token,
            orgId = business.id,
            portalUrl = "$portalBaseUrl/c/$token",
        )
    }

    private fun issueToken(business: Business): String {
        val token = generateSecureToken()
        business.accessToken = token
        business.tokenStatus = PENDING_TOKEN_STATUS
        businessRepository.save(business)
        log.info("Issued new portal token for org {}", business.id)
        return token
    }

    private fun generateSecureToken(): String {
        val bytes = ByteArray(TOKEN_BYTE_LENGTH)
        secureRandom.nextBytes(bytes)
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)
    }

    companion object {
        private const val MIN_TOKEN_LENGTH = 8
        private const val TOKEN_BYTE_LENGTH = 16
        private const val ACTIVE_STATUS = "active"
        private const val DEFAULT_PLAN_TIER = "starter"
        private const val PENDING_TOKEN_STATUS = "pending"
    }
}
