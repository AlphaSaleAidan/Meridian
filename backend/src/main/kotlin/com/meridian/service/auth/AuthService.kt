package com.meridian.service.auth

import com.meridian.dto.LoginRequest
import com.meridian.dto.SignupRequest

interface AuthService {
    suspend fun signup(request: SignupRequest)

    suspend fun login(request: LoginRequest): LoginResult
}

/**
 * Result of a successful Supabase login. The user id is what org-membership
 * checks key on (businesses.owner_user_id / business_users.user_id).
 */
data class LoginResult(
    val accessToken: String,
    val userId: String?,
)
