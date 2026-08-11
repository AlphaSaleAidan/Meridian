package com.meridian.integration

import com.meridian.exception.BadRequestException
import com.meridian.repository.AccessTokenRepository
import com.meridian.repository.BusinessRepository
import com.meridian.repository.OnboardingProgressRepository
import com.meridian.service.onboarding.OnboardingService
import com.meridian.support.PostgresIntegrationTest
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
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

    @Autowired
    private lateinit var onboardingService: OnboardingService

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
                        onboarded boolean NOT NULL DEFAULT false,
                        created_at timestamptz NOT NULL DEFAULT now()
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
                // Audit metadata (mirrors 20260811_audit_metadata.sql)
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS created_by text NOT NULL DEFAULT '00000000-0000-0000-0000-000000000037'",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS modified_at timestamptz",
                "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS modified_by text",
                "ALTER TABLE access_tokens ADD COLUMN IF NOT EXISTS modified_at timestamptz",
                "ALTER TABLE access_tokens ADD COLUMN IF NOT EXISTS modified_by text",
                "ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now()",
                "ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS created_by text NOT NULL DEFAULT '00000000-0000-0000-0000-000000000037'",
                "ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS modified_at timestamptz",
                "ALTER TABLE onboarding_progress ADD COLUMN IF NOT EXISTS modified_by text",
                // AFTER the email column exists (order matters on a fresh container)
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_businesses_email_uniq ON businesses(email)",
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

    // ── Flow-level (service through real Postgres, @Transactional engaged) ──

    @Test
    fun `redeem flow end-to-end - token flipped, business activated and owned, step recorded`() =
        runTest {
            val businessId = onboardingService.redeemForUser("mtk_valid", ownerId)

            assertEquals("biz_pre", businessId)
            assertNull(accessTokenRepository.findRedeemableToken("mtk_valid"))
            val owned = businessRepository.findByOwnerUserId(ownerId)
            assertTrue(owned.any { it.id == "biz_pre" && it.status == "active" && it.tokenStatus == "redeemed" })
            // Step row is there and idempotent
            assertEquals(0L, onboardingProgressRepository.recordStep("biz_pre", "token_redeemed", ownerId.toString()))
        }

    @Test
    fun `second redeem of the same token fails and does NOT steal ownership`() =
        runTest {
            val secondUser = UUID.fromString("55555555-5555-5555-5555-555555555555")
            onboardingService.redeemForUser("mtk_valid", ownerId)

            assertThrows<BadRequestException> {
                onboardingService.redeemForUser("mtk_valid", secondUser)
            }
            // First redeemer keeps the business
            assertTrue(businessRepository.findByOwnerUserId(ownerId).any { it.id == "biz_pre" })
            assertTrue(businessRepository.findByOwnerUserId(secondUser).isEmpty())
        }

    @Test
    fun `self-serve flow end-to-end - business created, owned and step recorded`() =
        runTest {
            val secondUser = UUID.fromString("66666666-6666-6666-6666-666666666666")
            val businessId =
                onboardingService.createBusinessForOwner(secondUser, "Flow Diner", null, "flow@diner.com")

            assertTrue(businessId.startsWith("biz_"))
            val owned = businessRepository.findByOwnerUserId(secondUser)
            assertTrue(owned.any { it.id == businessId && it.status == "active" })
            assertEquals(0L, onboardingProgressRepository.recordStep(businessId, "account_created", null))
        }

    @Test
    fun `self-serve flow rejects an email that already has a business`(): Unit =
        runTest {
            val secondUser = UUID.fromString("77777777-7777-7777-7777-777777777777")
            // jane@cafe.com is seeded on biz_pre
            assertThrows<BadRequestException> {
                onboardingService.createBusinessForOwner(secondUser, "Dupe Cafe", "Jane", "jane@cafe.com")
            }
            assertTrue(businessRepository.findByOwnerUserId(secondUser).isEmpty())
        }

    // ── Audit metadata (created_by / modified_at / modified_by stamping) ──

    @Test
    fun `redeem stamps modified metadata on the token and business with the acting user`() =
        runTest {
            onboardingService.redeemForUser("mtk_valid", ownerId)

            val tokenAudit = auditRow("SELECT modified_by, modified_at IS NOT NULL AS touched FROM access_tokens WHERE token = 'mtk_valid'")
            assertEquals(ownerId.toString(), tokenAudit.first)
            assertTrue(tokenAudit.second)
            val bizAudit = auditRow("SELECT modified_by, modified_at IS NOT NULL AS touched FROM businesses WHERE id = 'biz_pre'")
            assertEquals(ownerId.toString(), bizAudit.first)
            assertTrue(bizAudit.second)
        }

    @Test
    fun `self-serve create stamps created_by with the owner and recordStep falls back to the system actor`() =
        runTest {
            val user = UUID.fromString("88888888-8888-8888-8888-888888888888")
            val businessId = onboardingService.createBusinessForOwner(user, "Audit Cafe", null, "audit@cafe.com")

            val bizCreatedBy =
                databaseClient
                    .sql("SELECT created_by FROM businesses WHERE id = :id")
                    .bind("id", businessId)
                    .map { row, _ -> row.get("created_by", String::class.java) ?: "«missing»" }
                    .awaitSingle()
            assertEquals(user.toString(), bizCreatedBy)

            // Null completed_by → created_by falls back to AuditActor.SYSTEM
            onboardingProgressRepository.recordStep(businessId, "token_sent", null)
            val stepCreatedBy =
                databaseClient
                    .sql("SELECT created_by FROM onboarding_progress WHERE business_id = :id AND step_name = 'token_sent'")
                    .bind("id", businessId)
                    .map { row, _ -> row.get("created_by", String::class.java) ?: "«missing»" }
                    .awaitSingle()
            assertEquals("00000000-0000-0000-0000-000000000037", stepCreatedBy)
        }

    private suspend fun auditRow(sql: String): Pair<String?, Boolean> =
        databaseClient
            .sql(sql)
            .map { row, _ ->
                row.get("modified_by", String::class.java) to (row.get("touched", Boolean::class.javaObjectType) ?: false)
            }.awaitSingle()
}
