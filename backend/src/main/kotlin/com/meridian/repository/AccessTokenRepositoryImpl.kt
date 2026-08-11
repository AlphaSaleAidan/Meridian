package com.meridian.repository

import com.meridian.entity.PendingBusiness
import com.meridian.entity.RedeemableToken
import io.r2dbc.spi.Row
import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.awaitOneOrNull
import org.springframework.r2dbc.core.awaitRowsUpdated
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
class AccessTokenRepositoryImpl(
    private val databaseClient: DatabaseClient,
) : AccessTokenRepository {
    override suspend fun findPendingBusinessByToken(token: String): PendingBusiness? {
        val sql =
            """
            SELECT b.id AS business_id, b.name AS business_name, b.owner_name, b.email, b.business_type
            FROM access_tokens t
            JOIN businesses b ON b.id = t.business_id
            WHERE t.token = :token AND t.redeemed = false AND t.expires_at > now()
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("token", token)
            .map { row, _ -> mapPendingBusiness(row) }
            .awaitOneOrNull()
    }

    override suspend fun findRedeemableToken(token: String): RedeemableToken? {
        val sql =
            """
            SELECT id, business_id
            FROM access_tokens
            WHERE token = :token AND redeemed = false AND expires_at > now()
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("token", token)
            .map { row, _ ->
                RedeemableToken(
                    id =
                        row.get("id", UUID::class.java)
                            ?: throw IllegalStateException("Database row missing non-null primary key 'id'"),
                    businessId =
                        row.get("business_id", String::class.java)
                            ?: throw IllegalStateException("Database row missing non-null column 'business_id'"),
                )
            }.awaitOneOrNull()
    }

    override suspend fun markRedeemed(
        tokenId: UUID,
        userId: UUID,
    ): Long {
        val sql =
            """
            UPDATE access_tokens
            SET redeemed = true, redeemed_at = now(), redeemed_by = :userId,
                modified_at = now(), modified_by = :modifiedBy
            WHERE id = :tokenId AND redeemed = false
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("tokenId", tokenId)
            .bind("userId", userId)
            .bind("modifiedBy", userId.toString())
            .fetch()
            .awaitRowsUpdated()
    }

    private fun mapPendingBusiness(row: Row): PendingBusiness =
        PendingBusiness(
            businessId =
                row.get("business_id", String::class.java)
                    ?: throw IllegalStateException("Database row missing non-null column 'business_id'"),
            businessName = row.get("business_name", String::class.java),
            ownerName = row.get("owner_name", String::class.java),
            email = row.get("email", String::class.java),
            businessType = row.get("business_type", String::class.java),
        )
}
