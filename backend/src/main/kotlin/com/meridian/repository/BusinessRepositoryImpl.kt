package com.meridian.repository

import com.meridian.entity.Business
import io.r2dbc.spi.Row
import kotlinx.coroutines.flow.toList
import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.await
import org.springframework.r2dbc.core.awaitOneOrNull
import org.springframework.r2dbc.core.awaitRowsUpdated
import org.springframework.r2dbc.core.awaitSingle
import org.springframework.r2dbc.core.flow
import org.springframework.stereotype.Repository
import java.util.UUID

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

    override suspend fun findByOwnerUserId(ownerUserId: UUID): List<Business> {
        val sql =
            """
            SELECT id, name, plan_tier, access_token, token_status, status, pos_provider, onboarded
            FROM businesses
            WHERE owner_user_id = :ownerUserId
            ORDER BY created_at, id
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("ownerUserId", ownerUserId)
            .map { row, _ -> mapRow(row) }
            .flow()
            .toList()
    }

    override suspend fun insertOwnedBusiness(
        id: String,
        name: String,
        ownerName: String?,
        email: String,
        ownerUserId: UUID,
    ): String {
        val sql =
            """
            INSERT INTO businesses (id, name, owner_name, email, owner_user_id, status, created_by)
            VALUES (:id, :name, :ownerName, :email, :ownerUserId, 'active', :createdBy)
            RETURNING id
            """.trimIndent()

        var spec =
            databaseClient
                .sql(sql)
                .bind("id", id)
                .bind("name", name)
                .bind("email", email)
                .bind("ownerUserId", ownerUserId)
                .bind("createdBy", ownerUserId.toString())
        spec = ownerName?.let { spec.bind("ownerName", it) } ?: spec.bindNull("ownerName", String::class.java)
        return spec
            .map { row, _ ->
                row.get("id", String::class.java)
                    ?: throw IllegalStateException("INSERT ... RETURNING produced no id")
            }.awaitSingle()
    }

    override suspend fun activateForOwner(
        businessId: String,
        ownerUserId: UUID,
    ): Long {
        val sql =
            """
            UPDATE businesses
            SET token_status = 'redeemed', status = 'active', activated_at = now(), owner_user_id = :ownerUserId,
                modified_at = now(), modified_by = :modifiedBy
            WHERE id = :businessId
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("businessId", businessId)
            .bind("ownerUserId", ownerUserId)
            .bind("modifiedBy", ownerUserId.toString())
            .fetch()
            .awaitRowsUpdated()
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
                onboarded = EXCLUDED.onboarded,
                modified_at = now(),
                modified_by = '${AuditActor.SYSTEM}'
            """.trimIndent()

        databaseClient
            .sql(upsertSql)
            .bind("id", business.id)
            .bindNullable("name", business.name)
            .bindNullable("planTier", business.planTier)
            .bindNullable("accessToken", business.accessToken)
            .bindNullable("tokenStatus", business.tokenStatus)
            .bindNullable("status", business.status)
            .bindNullable("posProvider", business.posProvider)
            .bind("onboarded", business.onboarded)
            .await()
        return business
    }

    private fun DatabaseClient.GenericExecuteSpec.bindNullable(
        name: String,
        value: String?,
    ): DatabaseClient.GenericExecuteSpec = value?.let { bind(name, it) } ?: bindNull(name, String::class.java)

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
