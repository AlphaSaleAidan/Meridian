package com.meridian.service.auth

import com.meridian.dto.LoginRequest
import com.meridian.dto.SignupRequest

interface AuthService {
    suspend fun signup(request: SignupRequest)

    suspend fun login(request: LoginRequest): String
}
