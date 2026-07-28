package com.meridian.unit.service.auth

import com.meridian.exception.ForbiddenException
import com.meridian.exception.UnauthorizedException
import com.meridian.repository.BusinessRepository
import com.meridian.repository.BusinessUserRepository
import com.meridian.service.auth.OrgAccessService
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertDoesNotThrow
import org.junit.jupiter.api.assertThrows

class OrgAccessServiceTest {
    private val businessRepository = mockk<BusinessRepository>()
    private val businessUserRepository = mockk<BusinessUserRepository>()

    private fun service(enforcementDisabled: Boolean = false) =
        OrgAccessService(
            businessRepository = businessRepository,
            businessUserRepository = businessUserRepository,
            adminEmailsConfig = listOf("admin@test.com"),
            enforcementDisabled = enforcementDisabled,
        )

    @Test
    fun `admin email bypasses membership checks`() {
        assertDoesNotThrow {
            service().requireOrgAccess(userId = null, email = "Admin@Test.com", orgId = "org-1")
        }
        verify(exactly = 0) { businessRepository.existsByIdAndOwnerUserId(any(), any()) }
    }

    @Test
    fun `org owner is allowed`() {
        every { businessRepository.existsByIdAndOwnerUserId("org-1", "user-1") } returns true

        assertDoesNotThrow {
            service().requireOrgAccess(userId = "user-1", email = "owner@test.com", orgId = "org-1")
        }
    }

    @Test
    fun `active org member is allowed`() {
        every { businessRepository.existsByIdAndOwnerUserId("org-1", "user-2") } returns false
        every { businessUserRepository.existsByBusinessIdAndUserIdAndIsActiveTrue("org-1", "user-2") } returns true

        assertDoesNotThrow {
            service().requireOrgAccess(userId = "user-2", email = "member@test.com", orgId = "org-1")
        }
    }

    @Test
    fun `non-member is denied with ForbiddenException`() {
        every { businessRepository.existsByIdAndOwnerUserId("org-1", "user-3") } returns false
        every { businessUserRepository.existsByBusinessIdAndUserIdAndIsActiveTrue("org-1", "user-3") } returns false

        assertThrows<ForbiddenException> {
            service().requireOrgAccess(userId = "user-3", email = "stranger@test.com", orgId = "org-1")
        }
    }

    @Test
    fun `missing user id is unauthorized`() {
        assertThrows<UnauthorizedException> {
            service().requireOrgAccess(userId = null, email = "someone@test.com", orgId = "org-1")
        }
    }

    @Test
    fun `enforcement-disabled knob lets denied users through`() {
        every { businessRepository.existsByIdAndOwnerUserId("org-1", "user-3") } returns false
        every { businessUserRepository.existsByBusinessIdAndUserIdAndIsActiveTrue("org-1", "user-3") } returns false

        assertDoesNotThrow {
            service(enforcementDisabled = true).requireOrgAccess(userId = "user-3", email = "stranger@test.com", orgId = "org-1")
        }
    }
}
