package com.meridian.unit.service.auth

import com.meridian.repository.OrgMembershipRepository
import com.meridian.service.auth.OrgAccessServiceImpl
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class OrgAccessServiceTest {
    private val orgMembershipRepository = mockk<OrgMembershipRepository>()

    private fun service(enforcementDisabled: Boolean = false) =
        OrgAccessServiceImpl(
            orgMembershipRepository = orgMembershipRepository,
            adminEmailsConfig = listOf("admin@test.com"),
            enforcementDisabled = enforcementDisabled,
            virtualThreadDispatcher = Dispatchers.Unconfined,
        )

    @Test
    fun `admin email bypasses membership checks`() =
        runTest {
            assertTrue(service().hasOrgAccess(userId = null, email = "Admin@Test.com", orgId = "org-1"))
            verify(exactly = 0) { orgMembershipRepository.isOwner(any(), any()) }
        }

    @Test
    fun `org owner is allowed`() =
        runTest {
            every { orgMembershipRepository.isOwner("org-1", "user-1") } returns true

            assertTrue(service().hasOrgAccess(userId = "user-1", email = "owner@test.com", orgId = "org-1"))
        }

    @Test
    fun `active org member is allowed`() =
        runTest {
            every { orgMembershipRepository.isOwner("org-1", "user-2") } returns false
            every { orgMembershipRepository.isActiveMember("org-1", "user-2") } returns true

            assertTrue(service().hasOrgAccess(userId = "user-2", email = "member@test.com", orgId = "org-1"))
        }

    @Test
    fun `non-member is denied`() =
        runTest {
            every { orgMembershipRepository.isOwner("org-1", "user-3") } returns false
            every { orgMembershipRepository.isActiveMember("org-1", "user-3") } returns false

            assertFalse(service().hasOrgAccess(userId = "user-3", email = "stranger@test.com", orgId = "org-1"))
        }

    @Test
    fun `missing user id is denied without touching the db`() =
        runTest {
            assertFalse(service().hasOrgAccess(userId = null, email = "someone@test.com", orgId = "org-1"))
            verify(exactly = 0) { orgMembershipRepository.isOwner(any(), any()) }
            verify(exactly = 0) { orgMembershipRepository.isActiveMember(any(), any()) }
        }

    @Test
    fun `enforcement-disabled knob lets denied users through`() =
        runTest {
            every { orgMembershipRepository.isOwner("org-1", "user-3") } returns false
            every { orgMembershipRepository.isActiveMember("org-1", "user-3") } returns false

            assertTrue(service(enforcementDisabled = true).hasOrgAccess(userId = "user-3", email = "stranger@test.com", orgId = "org-1"))
        }
}
