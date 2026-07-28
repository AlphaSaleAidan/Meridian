package com.meridian.unit.service.auth

import com.meridian.dto.LoginRequest
import com.meridian.dto.SignupRequest
import com.meridian.exception.UnauthorizedException
import com.meridian.service.auth.SupabaseAuthServiceImpl
import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.client.engine.mock.toByteArray
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.headersOf
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import tools.jackson.databind.json.JsonMapper
import tools.jackson.module.kotlin.KotlinModule

class SupabaseAuthServiceImplTest {
    private val jsonMapper: JsonMapper = JsonMapper.builder().addModule(KotlinModule.Builder().build()).build()
    private val supabaseUrl = "http://localhost:54321"
    private val supabaseKey = "test-anon-key"

    private fun createService(mockEngine: MockEngine): SupabaseAuthServiceImpl {
        val httpClient =
            HttpClient(mockEngine) {
                expectSuccess = false
            }
        return SupabaseAuthServiceImpl(supabaseUrl, supabaseKey, httpClient, jsonMapper)
    }

    // ---- signup tests ----

    @Test
    fun `signup succeeds when Supabase returns 200`() =
        runTest {
            val engine =
                MockEngine { request ->
                    assertEquals("$supabaseUrl/auth/v1/signup", request.url.toString())
                    assertEquals("test-anon-key", request.headers["apikey"])
                    assertEquals(ContentType.Application.Json, request.body.contentType)

                    respond(
                        content = """{"id": "uuid-123", "email": "new@test.com"}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val service = createService(engine)
            // Should not throw
            service.signup(SignupRequest("new@test.com", "password123"))
        }

    @Test
    fun `signup throws UnauthorizedException when Supabase returns 422`() =
        runTest {
            val engine =
                MockEngine {
                    respond(
                        content = """{"error": "User already registered"}""",
                        status = HttpStatusCode.UnprocessableEntity,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val service = createService(engine)
            val exception =
                assertThrows<UnauthorizedException> {
                    service.signup(SignupRequest("existing@test.com", "password123"))
                }
            assertEquals("User already registered", exception.message)
        }

    @Test
    fun `signup throws UnauthorizedException when Supabase returns 400`() =
        runTest {
            val engine =
                MockEngine {
                    respond(
                        content = """{"error": "Password too short"}""",
                        status = HttpStatusCode.BadRequest,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val service = createService(engine)
            val exception =
                assertThrows<UnauthorizedException> {
                    service.signup(SignupRequest("user@test.com", "short"))
                }
            assertEquals("Password too short", exception.message)
        }

    // ---- login tests ----

    @Test
    fun `login returns access token on success`() =
        runTest {
            val engine =
                MockEngine { request ->
                    assertEquals(
                        "$supabaseUrl/auth/v1/token?grant_type=password",
                        request.url.toString(),
                    )
                    assertEquals("test-anon-key", request.headers["apikey"])

                    respond(
                        content = """{"access_token": "jwt-token-abc", "token_type": "bearer"}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val service = createService(engine)
            val token = service.login(LoginRequest("user@test.com", "password123"))
            assertEquals("jwt-token-abc", token)
        }

    @Test
    fun `login throws UnauthorizedException when Supabase returns 400`() =
        runTest {
            val engine =
                MockEngine {
                    respond(
                        content = """{"error": "invalid_grant", "error_description": "Invalid login credentials"}""",
                        status = HttpStatusCode.BadRequest,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val service = createService(engine)
            val exception =
                assertThrows<UnauthorizedException> {
                    service.login(LoginRequest("user@test.com", "wrong-password"))
                }
            assertEquals("Invalid login credentials", exception.message)
        }

    @Test
    fun `login sends correct JSON payload`() =
        runTest {
            val engine =
                MockEngine { request ->
                    val body = request.body.toByteArray().decodeToString()
                    val parsed = jsonMapper.readValue(body, Map::class.java)
                    assertEquals("user@test.com", parsed["email"])
                    assertEquals("secret123", parsed["password"])

                    respond(
                        content = """{"access_token": "tok", "token_type": "bearer"}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val service = createService(engine)
            service.login(LoginRequest("user@test.com", "secret123"))
        }
}
