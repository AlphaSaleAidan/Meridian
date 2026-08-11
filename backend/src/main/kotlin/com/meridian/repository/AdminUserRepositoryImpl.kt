package com.meridian.repository

import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.awaitSingle
import org.springframework.stereotype.Repository

@Repository
class AdminUserRepositoryImpl(
    private val databaseClient: DatabaseClient,
) : AdminUserRepository {
    override suspend fun existsByUserId(userId: String): Boolean {
        val sql =
            """
            SELECT EXISTS (
                SELECT 1 FROM admin_users WHERE user_id = CAST(:userId AS uuid)
            ) AS is_admin
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("userId", userId)
            .map { row, _ -> row.get("is_admin", Boolean::class.javaObjectType) ?: false }
            .awaitSingle()
    }
}
