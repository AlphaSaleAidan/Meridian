package com.meridian.integration

import com.meridian.repository.AdminUserRepository
import com.meridian.repository.BusinessRepository
import com.meridian.repository.BusinessUserRepository
import com.meridian.repository.SalesRepRepository
import com.meridian.service.user.UserIdentityService
import com.meridian.support.PostgresIntegrationTest
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.await
import org.springframework.r2dbc.core.awaitSingle
import java.util.UUID

/**
 * Exercises the identity repositories against real Postgres with the subset of
 * the Supabase schema they read (columns mirror supabase/migrations/20260429_001,
 * 20260429_003 and 20260512).
 */
@Tag("integration")
@SpringBootTest
class UserRepositoriesIntegrationTest : PostgresIntegrationTest() {
    @Autowired
    private lateinit var databaseClient: DatabaseClient

    @Autowired
    private lateinit var businessRepository: BusinessRepository

    @Autowired
    private lateinit var businessUserRepository: BusinessUserRepository

    @Autowired
    private lateinit var adminUserRepository: AdminUserRepository

    @Autowired
    private lateinit var salesRepRepository: SalesRepRepository

    @Autowired
    private lateinit var userIdentityService: UserIdentityService

    private val ownerId = UUID.fromString("11111111-1111-1111-1111-111111111111")
    private val staffId = UUID.fromString("22222222-2222-2222-2222-222222222222")
    private val strangerId = UUID.fromString("33333333-3333-3333-3333-333333333333")

    @BeforeEach
    fun setUpSchema() =
        runTest {
            val ddl =
                listOf(
                    """
                    CREATE TABLE IF NOT EXISTS businesses (
                        id text PRIMARY KEY,
                        name text,
                        plan_tier text,
                        access_token text,
                        token_status text,
                        status text,
                        pos_provider text,
                        onboarded boolean NOT NULL DEFAULT false,
                        owner_user_id uuid
                    )
                    """.trimIndent(),
                    """
                    CREATE TABLE IF NOT EXISTS business_users (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        business_id text NOT NULL,
                        user_id uuid,
                        email text NOT NULL,
                        full_name text,
                        role text NOT NULL DEFAULT 'staff',
                        location_id text,
                        is_active boolean NOT NULL DEFAULT true,
                        last_login_at timestamptz,
                        login_count integer NOT NULL DEFAULT 0
                    )
                    """.trimIndent(),
                    """
                    CREATE TABLE IF NOT EXISTS admin_users (
                        user_id uuid PRIMARY KEY,
                        email text NOT NULL
                    )
                    """.trimIndent(),
                    """
                    CREATE TABLE IF NOT EXISTS sales_reps (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        name text NOT NULL,
                        email text NOT NULL,
                        is_active boolean NOT NULL DEFAULT false
                    )
                    """.trimIndent(),
                )
            ddl.forEach { databaseClient.sql(it).await() }
            // Other test classes may have created `businesses` from init-local-db.sql,
            // which predates the owner linkage — the ALTER converges both shapes.
            databaseClient.sql("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS owner_user_id uuid").await()
            // Each test seeds from a clean slate; tables are shared across test classes.
            listOf("business_users", "businesses", "admin_users", "sales_reps").forEach {
                databaseClient.sql("DELETE FROM $it").await()
            }

            databaseClient
                .sql(
                    """
                    INSERT INTO businesses (id, name, status, onboarded, owner_user_id)
                    VALUES ('biz_owned', 'Owned Bistro', 'active', true, :ownerId),
                           ('biz_staffed', 'Staffed Diner', 'active', true, NULL)
                    """.trimIndent(),
                ).bind("ownerId", ownerId)
                .await()
            databaseClient
                .sql(
                    """
                    INSERT INTO business_users (business_id, user_id, email, role, location_id, is_active, login_count)
                    VALUES ('biz_staffed', :staffId, 'staff@test.com', 'manager', 'loc_1', true, 0),
                           ('biz_staffed', :strangerId, 'inactive@test.com', 'staff', NULL, false, 0),
                           ('biz_staffed', NULL, 'roster.only@placeholder.local', 'staff', NULL, true, 0)
                    """.trimIndent(),
                ).bind("staffId", staffId)
                .bind("strangerId", strangerId)
                .await()
            databaseClient
                .sql("INSERT INTO admin_users (user_id, email) VALUES (:id, 'admin@test.com')")
                .bind("id", ownerId)
                .await()
            databaseClient
                .sql(
                    """
                    INSERT INTO sales_reps (name, email, is_active)
                    VALUES ('Active Rep', 'rep@test.com', true),
                           ('Former Rep', 'former@test.com', false)
                    """.trimIndent(),
                ).await()
        }

    @Test
    fun `findByOwnerUserId returns owned businesses only`() =
        runTest {
            val owned = businessRepository.findByOwnerUserId(ownerId)

            assertEquals(listOf("biz_owned"), owned.map { it.id })
            assertEquals("Owned Bistro", owned.first().name)
            assertTrue(businessRepository.findByOwnerUserId(strangerId).isEmpty())
        }

    @Test
    fun `findActiveMembershipsByUserId joins business name and filters inactive rows`() =
        runTest {
            val memberships = businessUserRepository.findActiveMembershipsByUserId(staffId)

            assertEquals(1, memberships.size)
            val membership = memberships.first()
            assertEquals("biz_staffed", membership.businessId)
            assertEquals("Staffed Diner", membership.businessName)
            assertEquals("manager", membership.role)
            assertEquals("loc_1", membership.locationId)

            // Inactive membership resolves to nothing
            assertTrue(businessUserRepository.findActiveMembershipsByUserId(strangerId).isEmpty())
        }

    @Test
    fun `recordLogin stamps last_login_at and bumps login_count on active rows only`() =
        runTest {
            val touched = businessUserRepository.recordLogin(staffId)
            businessUserRepository.recordLogin(staffId)

            assertEquals(1L, touched)
            val row =
                databaseClient
                    .sql(
                        "SELECT login_count, last_login_at IS NOT NULL AS stamped FROM business_users " +
                            "WHERE user_id = :id",
                    ).bind("id", staffId)
                    .map { r, _ ->
                        Pair(
                            r.get("login_count", Int::class.javaObjectType) ?: 0,
                            r.get("stamped", Boolean::class.javaObjectType) ?: false,
                        )
                    }.awaitSingle()
            assertEquals(2, row.first)
            assertTrue(row.second)

            // Inactive membership is never stamped
            assertEquals(0L, businessUserRepository.recordLogin(strangerId))
        }

    @Test
    fun `existsByUserId reflects the admin_users grant table`() =
        runTest {
            assertTrue(adminUserRepository.existsByUserId(ownerId))
            assertFalse(adminUserRepository.existsByUserId(staffId))
        }

    @Test
    fun `existsActiveByEmail requires an active sales rep row`() =
        runTest {
            assertTrue(salesRepRepository.existsActiveByEmail("rep@test.com"))
            assertFalse(salesRepRepository.existsActiveByEmail("former@test.com"))
            assertFalse(salesRepRepository.existsActiveByEmail("nobody@test.com"))
        }

    // ── Flow-level (identity service through real Postgres) ──

    @Test
    fun `resolveIdentity flow - owner with admin grant gets owner role, org and flags`() =
        runTest {
            val identity = userIdentityService.resolveIdentity(ownerId, "admin@test.com", "Owner", isVerified = true)

            assertEquals("owner", identity.role)
            assertEquals("biz_owned", identity.orgId)
            assertTrue(identity.isAdmin)
            assertFalse(identity.isSalesRep)
            assertEquals(listOf("biz_owned"), identity.businesses.map { it.businessId })
        }

    @Test
    fun `resolveIdentity flow - staff member gets membership role, location and rep flag from email`() =
        runTest {
            val identity = userIdentityService.resolveIdentity(staffId, "rep@test.com", null, isVerified = false)

            assertEquals("manager", identity.role)
            assertEquals("biz_staffed", identity.orgId)
            assertEquals("loc_1", identity.locationId)
            assertFalse(identity.isAdmin)
            assertTrue(identity.isSalesRep)
        }

    @Test
    fun `resolveIdentity flow - unknown user resolves to staff with nothing`() =
        runTest {
            val nobody = UUID.fromString("99999999-9999-9999-9999-999999999999")
            val identity = userIdentityService.resolveIdentity(nobody, "nobody@test.com", null, isVerified = false)

            assertEquals("staff", identity.role)
            assertTrue(identity.businesses.isEmpty())
            assertFalse(identity.isAdmin)
            assertFalse(identity.isSalesRep)
        }
}
