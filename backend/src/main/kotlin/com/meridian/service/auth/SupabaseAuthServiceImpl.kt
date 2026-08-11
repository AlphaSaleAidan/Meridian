package com.meridian.service.auth

import com.meridian.dto.LoginRequest
import com.meridian.dto.SignupRequest
import com.meridian.exception.BadRequestException
import com.meridian.exception.UnauthorizedException
import io.ktor.client.HttpClient
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import org.slf4j.LoggerFactory
import tools.jackson.databind.json.JsonMapper
import tools.jackson.module.kotlin.readValue
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

class SupabaseAuthServiceImpl(
    private val supabaseUrl: String,
    private val supabaseKey: String,
    private val httpClient: HttpClient,
    private val jsonMapper: JsonMapper,
    private val passwordResetRedirectUrl: String = "",
) : AuthService {
    private val log = LoggerFactory.getLogger(SupabaseAuthServiceImpl::class.java)

    override suspend fun signup(request: SignupRequest): SupabaseUser {
        val url = "$supabaseUrl/auth/v1/signup"
        log.info("Attempting signup for {}", request.email)

        // display_name/business_name ride along as user_metadata for parity with
        // the SPA's signUp options.data — cosmetic only, never used for authz.
        val metadata =
            buildMap {
                request.displayName?.let { put("display_name", it) }
                request.businessName?.let { put("business_name", it) }
            }
        val payload =
            buildMap<String, Any> {
                put("email", request.email)
                put("password", request.password)
                if (metadata.isNotEmpty()) put("data", metadata)
            }

        val response =
            httpClient.post(url) {
                header("apikey", supabaseKey)
                contentType(ContentType.Application.Json)
                setBody(jsonMapper.writeValueAsString(payload))
            }

        if (!response.status.isSuccess()) {
            val errorBody = response.bodyAsText()
            log.error("Signup failed: {}", errorBody)
            val errorMessage =
                try {
                    val errorJson = jsonMapper.readValue<Map<String, Any>>(errorBody)
                    (
                        errorJson["msg"] ?: errorJson["error_description"] ?: errorJson["error"]
                            ?: "Signup failed. Please check your credentials."
                    ).toString()
                } catch (e: Exception) {
                    "Signup failed. Please check your credentials."
                }
            throw UnauthorizedException(errorMessage)
        }
        log.info("Signup successful for {}", request.email)

        val signupResponse = jsonMapper.readValue<SupabaseSignupResponse>(response.bodyAsText())
        return signupResponse.toUser()
            ?: throw IllegalStateException("Supabase signup succeeded but returned no user")
    }

    override suspend fun login(request: LoginRequest): SupabaseSession {
        val url = "$supabaseUrl/auth/v1/token?grant_type=password"
        log.info("Attempting login for {}", request.email)

        val payload =
            mapOf(
                "email" to request.email,
                "password" to request.password,
            )

        val response =
            httpClient.post(url) {
                header("apikey", supabaseKey)
                contentType(ContentType.Application.Json)
                setBody(jsonMapper.writeValueAsString(payload))
            }

        if (!response.status.isSuccess()) {
            val errorBody = response.bodyAsText()
            log.error("Login failed: {}", errorBody)
            val errorMessage =
                try {
                    val errorJson = jsonMapper.readValue<Map<String, Any>>(errorBody)
                    (errorJson["msg"] ?: errorJson["error_description"] ?: errorJson["error"] ?: "Invalid email or password.").toString()
                } catch (e: Exception) {
                    "Invalid email or password."
                }
            throw UnauthorizedException(errorMessage)
        }

        val responseBody = response.bodyAsText()
        val tokenResponse = jsonMapper.readValue<SupabaseTokenResponse>(responseBody)
        return SupabaseSession(accessToken = tokenResponse.accessToken, user = tokenResponse.user)
    }

    override suspend fun forgotPassword(email: String) {
        var url = "$supabaseUrl/auth/v1/recover"
        if (passwordResetRedirectUrl.isNotEmpty()) {
            url += "?redirect_to=" + URLEncoder.encode(passwordResetRedirectUrl, StandardCharsets.UTF_8)
        }

        val response =
            try {
                httpClient.post(url) {
                    header("apikey", supabaseKey)
                    contentType(ContentType.Application.Json)
                    setBody(jsonMapper.writeValueAsString(mapOf("email" to email)))
                }
            } catch (e: Exception) {
                log.error("forgot-password: transport error reaching Supabase recover", e)
                return
            }

        when {
            response.status.value == 429 ->
                log.error(
                    "forgot-password: Supabase recover rate-limited (429) — built-in SMTP 2/hr cap " +
                        "likely hit; configure custom SMTP. resp={}",
                    response.bodyAsText().take(200),
                )
            response.status.value >= 500 ->
                log.error("forgot-password: Supabase recover {}: {}", response.status.value, response.bodyAsText().take(200))
            !response.status.isSuccess() ->
                // Typically an unknown email — expected; keep it out of warn-level
                // logs so they don't become an enumeration oracle.
                log.debug("forgot-password: Supabase recover {}: {}", response.status.value, response.bodyAsText().take(200))
        }
    }

    override suspend fun resetPassword(
        accessToken: String,
        newPassword: String,
    ) {
        updatePassword(accessToken, newPassword, "reset-password")
        // The recovery session outlives the reset (the JWT is stateless and valid until
        // exp, and its refresh token could mint more). Revoke it so the emailed token
        // dies the moment it has done its job. Best-effort: the password DID change,
        // so a failed revoke must not fail the reset.
        revokeSession(accessToken, "reset-password")
    }

    override suspend fun changePassword(
        accessToken: String,
        newPassword: String,
    ) = updatePassword(accessToken, newPassword, "change-password")

    /** GoTrue logout, scope=local: revokes only the session behind this token (refresh token + session row). */
    private suspend fun revokeSession(
        accessToken: String,
        operation: String,
    ) {
        try {
            val response =
                httpClient.post("$supabaseUrl/auth/v1/logout?scope=local") {
                    header("apikey", supabaseKey)
                    header("Authorization", "Bearer $accessToken")
                }
            if (!response.status.isSuccess()) {
                log.warn("{}: session revoke returned {}", operation, response.status.value)
            }
        } catch (e: Exception) {
            log.warn("{}: session revoke failed", operation, e)
        }
    }

    /** PUT /auth/v1/user with the given user token — shared by reset (recovery token) and change (session token). */
    private suspend fun updatePassword(
        accessToken: String,
        newPassword: String,
        operation: String,
    ) {
        val response =
            httpClient.put("$supabaseUrl/auth/v1/user") {
                header("apikey", supabaseKey)
                header("Authorization", "Bearer $accessToken")
                contentType(ContentType.Application.Json)
                setBody(jsonMapper.writeValueAsString(mapOf("password" to newPassword)))
            }

        if (!response.status.isSuccess()) {
            val errorBody = response.bodyAsText()
            log.error("{} failed: {} {}", operation, response.status.value, errorBody.take(200))
            if (response.status.value == 401 || response.status.value == 403) {
                throw UnauthorizedException("Invalid or expired token")
            }
            val errorMessage =
                try {
                    val errorJson = jsonMapper.readValue<Map<String, Any>>(errorBody)
                    (errorJson["msg"] ?: errorJson["error_description"] ?: errorJson["error"] ?: "Password update failed.").toString()
                } catch (e: Exception) {
                    "Password update failed."
                }
            throw BadRequestException(errorMessage)
        }
        log.info("{} succeeded", operation)
    }
}
