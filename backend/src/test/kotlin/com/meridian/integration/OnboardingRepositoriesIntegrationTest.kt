package com.meridian.integration

import com.meridian.repository.AccessTokenRepository
import com.meridian.repository.BusinessRepository
import com.meridian.repository.OnboardingProgressRepository
import com.meridian.support.PostgresIntegrationTest
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.ValueSource
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.await
import org.springframework.r2dbc.core.awaitSingle
import java.util.UUID

/**
 * Exercises the invite-token + business-creation repositories against real
 * Postgres (schema subset of supabase/migrations/20260429_001).
 */
@Tag("integration")
@SpringBootTest
class OnboardingRepositoriesIntegrationTest : PostgresIntegrationTest() {
    @Autowired
    private lateinit var databaseClient: DatabaseClient

    @Autowired
    private lateinit var accessTokenRepository: AccessTokenRepository

    @Autowired
    private lateinit var businessRepository: BusinessRepository

    @Autowired
    private lateinit var onboardingProgressRepository: OnboardingProgressRepository

    private val ownerId = UUID.fromString("44444444-4444-4444-4444-444444444444")

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
                        onboarded boolean NOT NULL DEFAULT false
                    )
                    """.trimIndent(),
                    """
                    CREATE TABLE IF NOT EXISTS access_tokens (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        business_id text NOT NULL,
                        token text NOT NULL UNIQUE,
                        created_by text,
                        redeemed boolean NOT NULL DEFAULT false,
                        redeemed_at timestamptz,
                        redeemed_by uuid,
                        expires_at timestamptz NOT NULL DEFAULT (now() + INTERVAL '30 days'),
                        created_at timestamptz NOT NULL DEFAULT now()
                    )
                    """.trimIndent(),
                    """
                    CREATE TABLE IF NOT EXISTS onboarding_progress (
                        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                        business_id text NOT NULL,
                        step_name text NOT NULL,
                        completed_at timestamptz NOT NULL DEFAULT now(),
                        completed_by text,
                        notes text
                    )
                    """.trimIndent(),
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_onboarding_step ON onboarding_progress(business_id, step_name)",
                )
            ddl.forEach { databaseClient.sql(it).await() }
            // Converge shapes with other test classes / init-local-db.sql
            listOf(
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS owner_user_id uuid",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS owner_name text",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS email text",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS business_type text",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS activated_at timestamptz",
            ).forEach { databaseClient.sql(it).await() }
            listOf("access_tokens", "onboarding_progress", "businesses").forEach {
                databaseClient.sql("DELETE FROM $it").await()
            }

            databaseClient
                .sql(
                    """
                    INSERT INTO businesses (id, name, owner_name, email, status, token_status, business_type)
                    VALUES ('biz_pre', 'Pre Created Cafe', 'Jane Doe', 'jane@cafe.com', 'pending', 'pending', 'coffee_shop')
                    """.trimIndent(),
                ).await()
            databaseClient
                .sql(
                    """
                    INSERT INTO access_tokens (business_id, token, expires_at)
                    VALUES ('biz_pre', 'mtk_valid', now() + INTERVAL '1 day'),
                           ('biz_pre', 'mtk_expired', now() - INTERVAL '1 day')
                    """.trimIndent(),
                ).await()
            databaseClient
                .sql("INSERT INTO access_tokens (business_id, token, redeemed) VALUES ('biz_pre', 'mtk_used', true)")
                .await()
        }

    @Test
    fun `findPendingBusinessByToken joins the business for a valid token`() =
        runTest {
            val pending = accessTokenRepository.findPendingBusinessByToken("mtk_valid")

            assertNotNull(pending)
            assertEquals("biz_pre", pending!!.businessId)
            assertEquals("Pre Created Cafe", pending.businessName)
            assertEquals("Jane Doe", pending.ownerName)
            assertEquals("coffee_shop", pending.businessType)
        }

    @ParameterizedTest(name = "resolves nothing for {0} token")
    @ValueSource(strings = ["mtk_expired", "mtk_used", "mtk_nope"])
    fun `findPendingBusinessByToken rejects expired, redeemed and unknown tokens`(token: String) =
        runTest {
            assertNull(accessTokenRepository.findPendingBusinessByToken(token))
            assertNull(accessTokenRepository.findRedeemableToken(token))
        }

    @Test
    fun `markRedeemed flips the token exactly once`() =
        runTest {
            val redeemable = accessTokenRepository.findRedeemableToken("mtk_valid")
            assertNotNull(redeemable)

            assertEquals(1L, accessTokenRepository.markRedeemed(redeemable!!.id, ownerId))
            // Second attempt is a no-op — redeemed = false guard
            assertEquals(0L, accessTokenRepository.markRedeemed(redeemable.id, ownerId))
            assertNull(accessTokenRepository.findRedeemableToken("mtk_valid"))
        }

    @Test
    fun `activateForOwner binds and activates the pre-created business`() =
        runTest {
            assertEquals(1L, businessRepository.activateForOwner("biz_pre", ownerId))

            val row =
                databaseClient
                    .sql(
                        "SELECT status, token_status, owner_user_id, activated_at IS NOT NULL AS activated " +
                            "FROM businesses WHERE id = 'biz_pre'",
                    ).map { r, _ ->
                        Triple(
                            "${r.get("status", String::class.java)}/${r.get("token_status", String::class.java)}",
                            r.get("owner_user_id", UUID::class.java),
                            r.get("activated", Boolean::class.javaObjectType) ?: false,
                        )
                    }.awaitSingle()
            assertEquals("active/redeemed", row.first)
            assertEquals(ownerId, row.second)
            assertTrue(row.third)
        }

    @Test
    fun `insertOwnedBusiness creates an active owned business`() =
        runTest {
            val id =
                businessRepository.insertOwnedBusiness(
                    id = "biz_selfserve1",
                    name = "Self Serve Diner",
                    ownerName = "Sam",
                    email = "sam@diner.com",
                    ownerUserId = ownerId,
                )

            assertEquals("biz_selfserve1", id)
            val owned = businessRepository.findByOwnerUserId(ownerId)
            assertTrue(owned.any { it.id == "biz_selfserve1" && it.status == "active" })
        }

    @Test
    fun `recordStep is idempotent per business and step`() =
        runTest {
            assertEquals(1L, onboardingProgressRepository.recordStep("biz_pre", "token_redeemed", ownerId.toString()))
            assertEquals(0L, onboardingProgressRepository.recordStep("biz_pre", "token_redeemed", ownerId.toString()))
        }
}
