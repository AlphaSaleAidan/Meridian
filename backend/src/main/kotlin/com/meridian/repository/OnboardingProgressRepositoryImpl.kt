package com.meridian.repository

import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.awaitRowsUpdated
import org.springframework.stereotype.Repository

@Repository
class OnboardingProgressRepositoryImpl(
    private val databaseClient: DatabaseClient,
) : OnboardingProgressRepository {
    override suspend fun recordStep(
        businessId: String,
        stepName: String,
        completedBy: String?,
    ): Long {
        val sql =
            """
            INSERT INTO onboarding_progress (business_id, step_name, completed_by)
            VALUES (:businessId, :stepName, :completedBy)
            ON CONFLICT (business_id, step_name) DO NOTHING
            """.trimIndent()

        var spec =
            databaseClient
                .sql(sql)
                .bind("businessId", businessId)
                .bind("stepName", stepName)
        spec = completedBy?.let { spec.bind("completedBy", it) } ?: spec.bindNull("completedBy", String::class.java)
        return spec.fetch().awaitRowsUpdated()
    }
}
