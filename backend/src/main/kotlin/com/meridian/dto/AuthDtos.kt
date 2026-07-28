package com.meridian.dto

data class SignupRequest(
    val email: String,
    val password: String,
)

data class LoginRequest(
    val email: String,
    val password: String,
)

data class SessionInfoResponse(
    val email: String,
)
