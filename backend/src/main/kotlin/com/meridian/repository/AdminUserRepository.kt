package com.meridian.repository

import java.util.UUID

interface AdminUserRepository {
    /**
     * Whether this Supabase auth user id is a platform admin.
     * Mirrors the `is_admin()` SQL function used by the current SPA.
     */
    suspend fun existsByUserId(userId: UUID): Boolean
}
