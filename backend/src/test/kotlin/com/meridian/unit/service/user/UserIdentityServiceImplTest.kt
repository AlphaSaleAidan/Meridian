package com.meridian.unit.service.user

import com.meridian.entity.Business
import com.meridian.entity.BusinessMembership
import com.meridian.repository.AdminUserRepository
import com.meridian.repository.BusinessRepository
import com.meridian.repository.BusinessUserRepository
import com.meridian.repository.SalesRepRepository
import com.meridian.service.user.UserIdentityServiceImpl
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.util.UUID

class UserIdentityServiceImplTest {
    private val businessRepository = mockk<BusinessRepository>()
    private val businessUserRepository = mockk<BusinessUserRepository>()
    private val adminUserRepository = mockk<AdminUserRepository>()
    private val salesRepRepository = mockk<SalesRepRepository>()
    private val service =
        UserIdentityServiceImpl(
            businessRepository,
            businessUserRepository,
            adminUserRepository,
            salesRepRepository,
        )

    private fun stubDefaults(
        owned: List<Business> = emptyList(),
        memberships: List<BusinessMembership> = emptyList(),
        isAdmin: Boolean = false,
        isSalesRep: Boolean = false,
    ) {
        coEvery { businessRepository.findByOwnerUserId(any()) } returns owned
        coEvery { businessUserRepository.findActiveMembershipsByUserId(any()) } returns memberships
        coEvery { adminUserRepository.existsByUserId(any()) } returns isAdmin
        coEvery { salesRepRepository.existsActiveByEmail(any()) } returns isSalesRep
    }

    @Test
    fun `owner gets owner role and their business as primary org`() =
        runBlocking {
            stubDefaults(owned = listOf(Business(id = "biz_1", name = "Joe's Pizza")))

            val identity =
                service.resolveIdentity(
                    UUID.fromString("00000000-0000-0000-0000-000000000001"),
                    "joe@test.com",
                    "Joe",
                    isVerified = true,
                )

            assertEquals("owner", identity.role)
            assertEquals("biz_1", identity.orgId)
            assertEquals(1, identity.businesses.size)
            assertEquals("Joe's Pizza", identity.businesses.first().businessName)
            assertTrue(identity.isVerified)
        }

    @Test
    fun `staff member gets role and location from membership`() =
        runBlocking {
            stubDefaults(
                memberships =
                    listOf(
                        BusinessMembership(
                            businessId = "biz_2",
                            businessName = "Maple Tandoor",
                            role = "manager",
                            locationId = "loc_9",
                        ),
                    ),
            )

            val identity =
                service.resolveIdentity(
                    UUID.fromString("00000000-0000-0000-0000-000000000002"),
                    "staff@test.com",
                    null,
                    isVerified = false,
                )

            assertEquals("manager", identity.role)
            assertEquals("biz_2", identity.orgId)
            assertEquals("loc_9", identity.locationId)
            assertFalse(identity.isVerified)
        }

    @Test
    fun `ownership wins when an owner also has a business_users row for the same business`() =
        runBlocking {
            stubDefaults(
                owned = listOf(Business(id = "biz_1", name = "Joe's Pizza")),
                memberships =
                    listOf(
                        BusinessMembership(businessId = "biz_1", businessName = "Joe's Pizza", role = "staff"),
                        BusinessMembership(businessId = "biz_3", businessName = "Second Job", role = "staff"),
                    ),
            )

            val identity =
                service.resolveIdentity(
                    UUID.fromString("00000000-0000-0000-0000-000000000001"),
                    "joe@test.com",
                    "Joe",
                    isVerified = true,
                )

            assertEquals(2, identity.businesses.size)
            assertEquals("owner", identity.businesses.first { it.businessId == "biz_1" }.role)
            assertEquals("staff", identity.businesses.first { it.businessId == "biz_3" }.role)
            assertEquals("owner", identity.role)
        }

    @Test
    fun `user with no businesses defaults to staff role with no org`() =
        runBlocking {
            stubDefaults(isSalesRep = true)

            val identity =
                service.resolveIdentity(
                    UUID.fromString("00000000-0000-0000-0000-000000000003"),
                    "rep@test.com",
                    "Rep",
                    isVerified = true,
                )

            assertEquals("staff", identity.role)
            assertNull(identity.orgId)
            assertTrue(identity.businesses.isEmpty())
            assertTrue(identity.isSalesRep)
        }

    @Test
    fun `admin flag comes from admin_users grant table`() =
        runBlocking {
            stubDefaults(isAdmin = true)

            val identity =
                service.resolveIdentity(
                    UUID.fromString("00000000-0000-0000-0000-000000000004"),
                    "admin@test.com",
                    null,
                    isVerified = true,
                )

            assertTrue(identity.isAdmin)
            coVerify { adminUserRepository.existsByUserId(UUID.fromString("00000000-0000-0000-0000-000000000004")) }
            coVerify { salesRepRepository.existsActiveByEmail("admin@test.com") }
        }

    @Test
    fun `recordLogin delegates to business user repository`() =
        runBlocking {
            coEvery { businessUserRepository.recordLogin(UUID.fromString("00000000-0000-0000-0000-000000000005")) } returns 2L

            service.recordLogin(UUID.fromString("00000000-0000-0000-0000-000000000005"))

            coVerify { businessUserRepository.recordLogin(UUID.fromString("00000000-0000-0000-0000-000000000005")) }
        }
}
