package com.meridian.service.onboarding

import com.meridian.entity.PendingBusiness
import com.meridian.exception.BadRequestException
import com.meridian.exception.NotFoundException
import com.meridian.repository.AccessTokenRepository
import com.meridian.repository.BusinessRepository
import com.meridian.repository.OnboardingProgressRepository
import org.slf4j.LoggerFactory
import org.springframework.dao.DuplicateKeyException
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

        // Concurrent-redeem guard: two requests can both pass findRedeemableToken;
        // only the one whose UPDATE actually flips redeemed=false may proceed —
        // otherwise the loser would overwrite the winner's owner_user_id.
        if (accessTokenRepository.markRedeemed(redeemable.id, userId) == 0L) {
            throw BadRequestException("Invalid or expired access token")
        }
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
        try {
            businessRepository.insertOwnedBusiness(
                id = businessId,
                name = businessName,
                // businesses.owner_name is NOT NULL — fall back to the business name
                ownerName = ownerName ?: businessName,
                email = email,
                ownerUserId = userId,
            )
        } catch (e: DuplicateKeyException) {
            // businesses.email is UNIQUE — e.g. a rep already pre-created a business
            // for this email; the customer should use their invite link instead.
            throw BadRequestException("A business already exists for this email — use your invite link or contact support.")
        }
        onboardingProgressRepository.recordStep(businessId, STEP_ACCOUNT_CREATED, userId.toString())

        log.info("Self-serve business {} created", businessId)
        return businessId
    }

    companion object {
        private const val STEP_TOKEN_REDEEMED = "token_redeemed"
        private const val STEP_ACCOUNT_CREATED = "account_created"
    }
}
