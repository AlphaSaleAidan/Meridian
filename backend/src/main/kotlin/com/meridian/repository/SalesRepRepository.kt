package com.meridian.repository

interface SalesRepRepository {
    /**
     * Whether this email belongs to an active sales rep.
     * Mirrors the SPA's `checkIsSalesRep` lookup on `sales_reps`.
     */
    suspend fun existsActiveByEmail(email: String): Boolean
}
