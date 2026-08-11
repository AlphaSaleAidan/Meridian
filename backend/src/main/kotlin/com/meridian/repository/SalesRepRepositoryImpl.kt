package com.meridian.repository

import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.awaitSingle
import org.springframework.stereotype.Repository

@Repository
class SalesRepRepositoryImpl(
    private val databaseClient: DatabaseClient,
) : SalesRepRepository {
    override suspend fun existsActiveByEmail(email: String): Boolean {
        val sql =
            """
            SELECT EXISTS (
                SELECT 1 FROM sales_reps WHERE email = :email AND is_active
            ) AS is_rep
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("email", email)
            .map { row, _ -> row.get("is_rep", Boolean::class.javaObjectType) ?: false }
            .awaitSingle()
    }
}
