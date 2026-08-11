package com.meridian.service.auth

import com.meridian.dto.LoginRequest
import com.meridian.dto.SignupRequest
import com.meridian.exception.UnauthorizedException
import io.ktor.client.HttpClient
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import org.slf4j.LoggerFactory
import tools.jackson.databind.json.JsonMapper
import tools.jackson.module.kotlin.readValue

class SupabaseAuthServiceImpl(
    private val supabaseUrl: String,
    private val supabaseKey: String,
    private val httpClient: HttpClient,
    private val jsonMapper: JsonMapper,
) : AuthService {
    private val log = LoggerFactory.getLogger(SupabaseAuthServiceImpl::class.java)

    override suspend fun signup(request: SignupRequest) {
        val url = "$supabaseUrl/auth/v1/signup"
        log.info("Attempting signup for {}", request.email)

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
}
