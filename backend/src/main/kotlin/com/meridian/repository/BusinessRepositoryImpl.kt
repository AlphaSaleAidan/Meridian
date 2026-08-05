package com.meridian.repository

import com.meridian.entity.Business
import io.r2dbc.spi.Row
import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.await
import org.springframework.r2dbc.core.awaitOneOrNull
import org.springframework.stereotype.Repository

@Repository
class BusinessRepositoryImpl(
    private val databaseClient: DatabaseClient,
) : BusinessRepository {
    override suspend fun findById(id: String): Business? {
        val sql =
            """
            SELECT id, name, plan_tier, access_token, token_status, status, pos_provider, onboarded
            FROM businesses
            WHERE id = :id
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("id", id)
            .map { row, _ -> mapRow(row) }
            .awaitOneOrNull()
    }

    override suspend fun findByAccessTokenAndStatus(
        accessToken: String,
        status: String,
    ): Business? {
        val sql =
            """
            SELECT id, name, plan_tier, access_token, token_status, status, pos_provider, onboarded
            FROM businesses
            WHERE access_token = :accessToken AND status = :status
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("accessToken", accessToken)
            .bind("status", status)
            .map { row, _ -> mapRow(row) }
            .awaitOneOrNull()
    }

    override suspend fun save(business: Business): Business {
        val upsertSql =
            """
            INSERT INTO businesses (id, name, plan_tier, access_token, token_status, status, pos_provider, onboarded)
            VALUES (:id, :name, :planTier, :accessToken, :tokenStatus, :status, :posProvider, :onboarded)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                plan_tier = EXCLUDED.plan_tier,
                access_token = EXCLUDED.access_token,
                token_status = EXCLUDED.token_status,
                status = EXCLUDED.status,
                pos_provider = EXCLUDED.pos_provider,
                onboarded = EXCLUDED.onboarded
            """.trimIndent()

        val spec =
            databaseClient
                .sql(upsertSql)
                .bind("id", business.id)

        val withName = business.name?.let { spec.bind("name", it) } ?: spec.bindNull("name", String::class.java)
        val withPlan = business.planTier?.let { withName.bind("planTier", it) } ?: withName.bindNull("planTier", String::class.java)
        val withToken =
            business.accessToken?.let { withPlan.bind("accessToken", it) } ?: withPlan.bindNull("accessToken", String::class.java)
        val withTokenStatus =
            business.tokenStatus?.let { withToken.bind("tokenStatus", it) } ?: withToken.bindNull("tokenStatus", String::class.java)
        val withStatus =
            business.status?.let { withTokenStatus.bind("status", it) } ?: withTokenStatus.bindNull("status", String::class.java)
        val withPos =
            business.posProvider?.let { withStatus.bind("posProvider", it) } ?: withStatus.bindNull("posProvider", String::class.java)
        val withOnboarded = withPos.bind("onboarded", business.onboarded)

        withOnboarded.await()
        return business
    }

    private fun mapRow(row: Row): Business =
        Business(
            id =
                row.get("id", String::class.java)
                    ?: throw IllegalStateException("Database row missing non-null primary key 'id'"),
            name = row.get("name", String::class.java),
            planTier = row.get("plan_tier", String::class.java),
            accessToken = row.get("access_token", String::class.java),
            tokenStatus = row.get("token_status", String::class.java),
            status = row.get("status", String::class.java),
            posProvider = row.get("pos_provider", String::class.java),
            onboarded = row.get("onboarded", Boolean::class.javaObjectType) ?: false,
        )
}
