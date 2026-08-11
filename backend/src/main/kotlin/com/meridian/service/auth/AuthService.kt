package com.meridian.service.auth

import com.meridian.dto.LoginRequest
import com.meridian.dto.SignupRequest

interface AuthService {
    /** Registers the credentials with Supabase and returns the created (or pending-confirmation) user. */
    suspend fun signup(request: SignupRequest): SupabaseUser

    /** Verifies credentials with Supabase and returns the token plus the authenticated user. */
    suspend fun login(request: LoginRequest): SupabaseSession

    /**
     * Triggers Supabase's password-recovery email. NEVER throws on failure —
     * the caller must always answer with a generic success (anti-enumeration);
     * infrastructure failures (429 SMTP cap, 5xx) are surfaced in logs only.
     */
    suspend fun forgotPassword(email: String)

    /** Sets a new password using the recovery token from the reset email link. */
    suspend fun resetPassword(
        accessToken: String,
        newPassword: String,
    )

    /** Sets a new password for a logged-in user via the session's Supabase token. */
    suspend fun changePassword(
        accessToken: String,
        newPassword: String,
    )
}
