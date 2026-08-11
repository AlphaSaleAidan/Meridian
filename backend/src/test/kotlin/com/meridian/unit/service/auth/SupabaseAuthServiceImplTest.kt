package com.meridian.unit.service.auth

import com.meridian.dto.LoginRequest
import com.meridian.dto.SignupRequest
import com.meridian.exception.BadRequestException
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
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.ValueSource
import tools.jackson.databind.json.JsonMapper
import tools.jackson.module.kotlin.KotlinModule

class SupabaseAuthServiceImplTest {
    private val jsonMapper: JsonMapper = JsonMapper.builder().addModule(KotlinModule.Builder().build()).build()
    private val supabaseUrl = "http://localhost:54321"
    private val supabaseKey = "test-anon-key"

    private fun createService(
        mockEngine: MockEngine,
        passwordResetRedirectUrl: String = "",
    ): SupabaseAuthServiceImpl {
        val httpClient =
            HttpClient(mockEngine) {
                expectSuccess = false
            }
        return SupabaseAuthServiceImpl(supabaseUrl, supabaseKey, httpClient, jsonMapper, passwordResetRedirectUrl)
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
            val user = service.signup(SignupRequest("new@test.com", "password123"))
            assertEquals("uuid-123", user.id)
            assertEquals("new@test.com", user.email)
        }

    @Test
    fun `signup sends display and business name as user_metadata and parses a nested user`() =
        runTest {
            val engine =
                MockEngine { request ->
                    val body = request.body.toByteArray().decodeToString()
                    val parsed = jsonMapper.readValue(body, Map::class.java)
                    val data = parsed["data"] as Map<*, *>
                    assertEquals("Joe", data["display_name"])
                    assertEquals("Joe's Pizza", data["business_name"])
                    respond(
                        content =
                            """{"access_token": "tok", "user": {"id": "uuid-9", "email": "joe@test.com"}}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val user =
                createService(engine).signup(
                    SignupRequest("joe@test.com", "password123", displayName = "Joe", businessName = "Joe's Pizza"),
                )
            assertEquals("uuid-9", user.id)
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

    @Test
    fun `signup rejects an already-registered email disguised as a fabricated user`() =
        runTest {
            // GoTrue anti-enumeration: 200 + fake user with EMPTY identities
            val engine =
                MockEngine {
                    respond(
                        content = """{"id": "uuid-fake", "email": "taken@test.com", "identities": []}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            assertThrows<BadRequestException> {
                createService(engine).signup(SignupRequest("taken@test.com", "password123"))
            }
        }

    @Test
    fun `signup accepts a genuinely new user with identities present`() =
        runTest {
            val engine =
                MockEngine {
                    respond(
                        content =
                            """{"id": "uuid-123", "email": "new@test.com",
                               "identities": [{"id": "uuid-123"}]}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            assertEquals("uuid-123", createService(engine).signup(SignupRequest("new@test.com", "password123")).id)
        }

    // ---- login tests ----

    @Test
    fun `login returns access token and typed user on success`() =
        runTest {
            val engine =
                MockEngine { request ->
                    assertEquals(
                        "$supabaseUrl/auth/v1/token?grant_type=password",
                        request.url.toString(),
                    )
                    assertEquals("test-anon-key", request.headers["apikey"])

                    respond(
                        content =
                            """{"access_token": "jwt-token-abc", "token_type": "bearer",
                               "user": {"id": "uuid-1", "email": "user@test.com", "user_metadata": {"display_name": "U"}}}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val service = createService(engine)
            val session = service.login(LoginRequest("user@test.com", "password123"))
            assertEquals("jwt-token-abc", session.accessToken)
            assertEquals("uuid-1", session.user.id)
            assertEquals("user@test.com", session.user.email)
            assertEquals("U", session.user.userMetadata?.displayName)
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
                        content =
                            """{"access_token": "tok", "token_type": "bearer",
                               "user": {"id": "uuid-1", "email": "user@test.com", "user_metadata": {"display_name": "U"}}}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val service = createService(engine)
            service.login(LoginRequest("user@test.com", "secret123"))
        }

    // ---- forgot-password tests ----

    @Test
    fun `forgotPassword posts to recover without redirect when unconfigured`() =
        runTest {
            val engine =
                MockEngine { request ->
                    assertEquals("$supabaseUrl/auth/v1/recover", request.url.toString())
                    assertEquals("test-anon-key", request.headers["apikey"])
                    respond(
                        content = """{}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            createService(engine).forgotPassword("user@test.com")
        }

    @Test
    fun `forgotPassword appends url-encoded redirect_to when configured`() =
        runTest {
            val engine =
                MockEngine { request ->
                    assertEquals(
                        "$supabaseUrl/auth/v1/recover?redirect_to=https%3A%2F%2Fmeridian.tips%2Freset",
                        request.url.toString(),
                    )
                    respond(
                        content = """{}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            createService(engine, passwordResetRedirectUrl = "https://meridian.tips/reset")
                .forgotPassword("user@test.com")
        }

    @Test
    fun `forgotPassword swallows 429 rate limit (anti-enumeration, ops-log only)`() =
        runTest {
            val engine =
                MockEngine {
                    respond(
                        content = """{"msg": "over_email_send_rate_limit"}""",
                        status = HttpStatusCode.TooManyRequests,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            // Must not throw
            createService(engine).forgotPassword("user@test.com")
        }

    @ParameterizedTest(name = "swallows {0}")
    @ValueSource(ints = [422, 500, 503])
    fun `forgotPassword swallows non-2xx statuses (anti-enumeration)`(status: Int) =
        runTest {
            val engine =
                MockEngine {
                    respond(
                        content = """{"msg": "boom"}""",
                        status = HttpStatusCode.fromValue(status),
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }
            // Must not throw regardless of status
            createService(engine).forgotPassword("user@test.com")
        }

    // ---- reset/change password tests ----

    @Test
    fun `resetPassword puts new password then revokes the recovery session`() =
        runTest {
            val requests = mutableListOf<String>()
            val engine =
                MockEngine { request ->
                    requests += "${request.method.value} ${request.url}"
                    assertEquals("Bearer recovery-token", request.headers["Authorization"])
                    assertEquals("test-anon-key", request.headers["apikey"])
                    if (request.url.encodedPath.endsWith("/auth/v1/user")) {
                        val body = request.body.toByteArray().decodeToString()
                        val parsed = jsonMapper.readValue(body, Map::class.java)
                        assertEquals("new-secret-123", parsed["password"])
                    }
                    respond(
                        content = """{"id": "uuid-1"}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            createService(engine).resetPassword("recovery-token", "new-secret-123")

            assertEquals(
                listOf(
                    "PUT $supabaseUrl/auth/v1/user",
                    "POST $supabaseUrl/auth/v1/logout?scope=local",
                ),
                requests,
            )
        }

    @Test
    fun `resetPassword still succeeds when the session revoke fails`() =
        runTest {
            val engine =
                MockEngine { request ->
                    if (request.url.encodedPath.endsWith("/auth/v1/user")) {
                        respond(
                            content = """{"id": "uuid-1"}""",
                            status = HttpStatusCode.OK,
                            headers = headersOf(HttpHeaders.ContentType, "application/json"),
                        )
                    } else {
                        respond(
                            content = """{"msg": "boom"}""",
                            status = HttpStatusCode.InternalServerError,
                            headers = headersOf(HttpHeaders.ContentType, "application/json"),
                        )
                    }
                }

            // Best-effort revoke: must not throw — the password DID change
            createService(engine).resetPassword("recovery-token", "new-secret-123")
        }

    @Test
    fun `changePassword does not revoke the fresh session`() =
        runTest {
            val requests = mutableListOf<String>()
            val engine =
                MockEngine { request ->
                    requests += "${request.method.value} ${request.url.encodedPath}"
                    respond(
                        content = """{"id": "uuid-1"}""",
                        status = HttpStatusCode.OK,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            createService(engine).changePassword("session-token", "new-secret-123")

            // The fresh token becomes the HTTP session's stored token — revoking it would break later proxied calls
            assertEquals(listOf("PUT /auth/v1/user"), requests)
        }

    @ParameterizedTest(name = "throws UnauthorizedException on {0}")
    @ValueSource(ints = [401, 403])
    fun `resetPassword throws UnauthorizedException on an expired or forbidden token`(status: Int) =
        runTest {
            val engine =
                MockEngine {
                    respond(
                        content = """{"msg": "token is expired"}""",
                        status = HttpStatusCode.fromValue(status),
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            assertThrows<UnauthorizedException> {
                createService(engine).resetPassword("stale-token", "new-secret-123")
            }
        }

    @Test
    fun `changePassword surfaces Supabase validation message as BadRequestException`() =
        runTest {
            val engine =
                MockEngine {
                    respond(
                        content = """{"msg": "Password should be at least 6 characters."}""",
                        status = HttpStatusCode.UnprocessableEntity,
                        headers = headersOf(HttpHeaders.ContentType, "application/json"),
                    )
                }

            val exception =
                assertThrows<BadRequestException> {
                    createService(engine).changePassword("session-token", "short")
                }
            assertEquals("Password should be at least 6 characters.", exception.message)
        }
}
