package com.meridian.unit.service.onboarding

import com.meridian.entity.PendingBusiness
import com.meridian.entity.RedeemableToken
import com.meridian.exception.BadRequestException
import com.meridian.exception.NotFoundException
import com.meridian.repository.AccessTokenRepository
import com.meridian.repository.BusinessRepository
import com.meridian.repository.OnboardingProgressRepository
import com.meridian.service.onboarding.OnboardingServiceImpl
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.util.UUID

class OnboardingServiceImplTest {
    private val accessTokenRepository = mockk<AccessTokenRepository>()
    private val businessRepository = mockk<BusinessRepository>()
    private val onboardingProgressRepository = mockk<OnboardingProgressRepository>()
    private val service =
        OnboardingServiceImpl(
            accessTokenRepository,
            businessRepository,
            onboardingProgressRepository,
        )

    private val userId = UUID.fromString("00000000-0000-0000-0000-000000000001")
    private val tokenId = UUID.fromString("00000000-0000-0000-0000-00000000000a")

    @Test
    fun `validateToken returns the pending business`() =
        runBlocking {
            val pending = PendingBusiness(businessId = "biz_pre", businessName = "Pre Created", ownerName = "Joe")
            coEvery { accessTokenRepository.findPendingBusinessByToken("mtk_abc") } returns pending

            assertEquals(pending, service.validateToken("mtk_abc"))
        }

    @Test
    fun `validateToken throws NotFoundException for an unknown token`(): Unit =
        runBlocking {
            coEvery { accessTokenRepository.findPendingBusinessByToken("mtk_bad") } returns null

            assertThrows<NotFoundException> {
                service.validateToken("mtk_bad")
            }
        }

    @Test
    fun `redeemForUser marks the token, activates the business and records the step`() =
        runBlocking {
            coEvery { accessTokenRepository.findRedeemableToken("mtk_abc") } returns
                RedeemableToken(id = tokenId, businessId = "biz_pre")
            coEvery { accessTokenRepository.markRedeemed(tokenId, userId) } returns 1L
            coEvery { businessRepository.activateForOwner("biz_pre", userId) } returns 1L
            coEvery {
                onboardingProgressRepository.recordStep("biz_pre", "token_redeemed", userId.toString())
            } returns 1L

            val businessId = service.redeemForUser("mtk_abc", userId)

            assertEquals("biz_pre", businessId)
            coVerify { accessTokenRepository.markRedeemed(tokenId, userId) }
            coVerify { businessRepository.activateForOwner("biz_pre", userId) }
            coVerify { onboardingProgressRepository.recordStep("biz_pre", "token_redeemed", userId.toString()) }
        }

    @Test
    fun `redeemForUser throws when the token was redeemed after validate (race)`(): Unit =
        runBlocking {
            coEvery { accessTokenRepository.findRedeemableToken("mtk_gone") } returns null

            assertThrows<BadRequestException> {
                service.redeemForUser("mtk_gone", userId)
            }
            coVerify(exactly = 0) { accessTokenRepository.markRedeemed(any(), any()) }
        }

    @Test
    fun `createBusinessForOwner inserts with a generated biz id and records the step`() =
        runBlocking {
            val idSlot = slot<String>()
            coEvery {
                businessRepository.insertOwnedBusiness(
                    id = capture(idSlot),
                    name = "Joe's Pizza",
                    ownerName = "Joe",
                    email = "joe@test.com",
                    ownerUserId = userId,
                )
            } answers { idSlot.captured }
            coEvery {
                onboardingProgressRepository.recordStep(any(), "account_created", userId.toString())
            } returns 1L

            val businessId = service.createBusinessForOwner(userId, "Joe's Pizza", "Joe", "joe@test.com")

            assertTrue(businessId.startsWith("biz_"))
            assertEquals(36, businessId.length) // biz_ + 32 hex chars, matching the DB default shape
            coVerify { onboardingProgressRepository.recordStep(businessId, "account_created", userId.toString()) }
        }
}
