package com.meridian.repository

import com.meridian.entity.BusinessMembership
import io.r2dbc.spi.Row
import kotlinx.coroutines.flow.toList
import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.awaitRowsUpdated
import org.springframework.r2dbc.core.flow
import org.springframework.stereotype.Repository
import java.util.UUID

@Repository
class BusinessUserRepositoryImpl(
    private val databaseClient: DatabaseClient,
) : BusinessUserRepository {
    override suspend fun findActiveMembershipsByUserId(userId: UUID): List<BusinessMembership> {
        val sql =
            """
            SELECT bu.business_id, b.name AS business_name, bu.role, bu.location_id
            FROM business_users bu
            LEFT JOIN businesses b ON b.id = bu.business_id
            WHERE bu.user_id = :userId AND bu.is_active
            ORDER BY CASE WHEN bu.role = 'manager' THEN 0 ELSE 1 END, bu.business_id
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("userId", userId)
            .map { row, _ -> mapRow(row) }
            .flow()
            .toList()
    }

    override suspend fun recordLogin(userId: UUID): Long {
        val sql =
            """
            UPDATE business_users
            SET last_login_at = now(), login_count = login_count + 1
            WHERE user_id = :userId AND is_active
            """.trimIndent()

        return databaseClient
            .sql(sql)
            .bind("userId", userId)
            .fetch()
            .awaitRowsUpdated()
    }

    private fun mapRow(row: Row): BusinessMembership =
        BusinessMembership(
            businessId =
                row.get("business_id", String::class.java)
                    ?: throw IllegalStateException("Database row missing non-null column 'business_id'"),
            businessName = row.get("business_name", String::class.java),
            role = row.get("role", String::class.java) ?: "staff",
            locationId = row.get("location_id", String::class.java),
        )
}
