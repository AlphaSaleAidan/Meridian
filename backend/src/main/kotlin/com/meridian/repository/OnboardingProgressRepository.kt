package com.meridian.repository

interface OnboardingProgressRepository {
    /**
     * Records an onboarding step for a business. Idempotent — the table has a
     * unique (business_id, step_name) index and conflicts are ignored, matching
     * the SQL functions this replaces.
     */
    suspend fun recordStep(
        businessId: String,
        stepName: String,
        completedBy: String?,
    ): Long
}
