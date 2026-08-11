package com.meridian.service.auth

import com.meridian.dto.LoginRequest
import com.meridian.dto.SignupRequest

interface AuthService {
    suspend fun signup(request: SignupRequest)

    /** Verifies credentials with Supabase and returns the token plus the authenticated user. */
    suspend fun login(request: LoginRequest): SupabaseSession
}
