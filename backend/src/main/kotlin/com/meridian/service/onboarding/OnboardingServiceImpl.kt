package com.meridian.service.onboarding

import com.meridian.entity.PendingBusiness
import com.meridian.exception.BadRequestException
import com.meridian.exception.NotFoundException
import com.meridian.repository.AccessTokenRepository
import com.meridian.repository.BusinessRepository
import com.meridian.repository.OnboardingProgressRepository
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.util.UUID

@Service
class OnboardingServiceImpl(
    private val accessTokenRepository: AccessTokenRepository,
    private val businessRepository: BusinessRepository,
    private val onboardingProgressRepository: OnboardingProgressRepository,
) : OnboardingService {
    private val log = LoggerFactory.getLogger(OnboardingServiceImpl::class.java)

    override suspend fun validateToken(token: String): PendingBusiness =
        accessTokenRepository.findPendingBusinessByToken(token)
            ?: throw NotFoundException("Invalid or expired access token")

    @Transactional
    override suspend fun redeemForUser(
        token: String,
        userId: UUID,
    ): String {
        // Re-check inside the transaction — the token may have been redeemed
        // between the pre-signup validate and now.
        val redeemable =
            accessTokenRepository.findRedeemableToken(token)
                ?: throw BadRequestException("Invalid or expired access token")

        accessTokenRepository.markRedeemed(redeemable.id, userId)
        businessRepository.activateForOwner(redeemable.businessId, userId)
        onboardingProgressRepository.recordStep(redeemable.businessId, STEP_TOKEN_REDEEMED, userId.toString())

        log.info("Invite token redeemed for business {}", redeemable.businessId)
        return redeemable.businessId
    }

    @Transactional
    override suspend fun createBusinessForOwner(
        userId: UUID,
        businessName: String,
        ownerName: String?,
        email: String,
    ): String {
        // Id generated here (matching the DB default's biz_<hex> shape) so the
        // insert never depends on a column default being present.
        val businessId = "biz_" + UUID.randomUUID().toString().replace("-", "")
        businessRepository.insertOwnedBusiness(
            id = businessId,
            name = businessName,
            ownerName = ownerName,
            email = email,
            ownerUserId = userId,
        )
        onboardingProgressRepository.recordStep(businessId, STEP_ACCOUNT_CREATED, userId.toString())

        log.info("Self-serve business {} created", businessId)
        return businessId
    }

    companion object {
        private const val STEP_TOKEN_REDEEMED = "token_redeemed"
        private const val STEP_ACCOUNT_CREATED = "account_created"
    }
}
