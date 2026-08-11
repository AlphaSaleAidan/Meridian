package com.meridian.repository

import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.awaitSingle
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
class AdminUserRepositoryImpl(
    private val databaseClient: DatabaseClient,
) : AdminUserRepository {
    override suspend fun existsByUserId(userId: UUID): Boolean {
        val sql =
            """
            SELECT EXISTS (
                SELECT 1 FROM admin_users WHERE user_id = :userId
            ) AS is_admin
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("userId", userId)
            .map { row, _ -> row.get("is_admin", Boolean::class.javaObjectType) ?: false }
            .awaitSingle()
    }
}
