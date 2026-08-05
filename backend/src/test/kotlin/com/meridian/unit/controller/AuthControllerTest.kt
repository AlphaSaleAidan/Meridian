package com.meridian.unit.controller

import com.meridian.controller.AuthController
import com.meridian.dto.LoginRequest
import com.meridian.dto.SignupRequest
import com.meridian.exception.UnauthorizedException
import com.meridian.security.SecurityConstants
import com.meridian.service.auth.AuthService
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.verify
import jakarta.servlet.http.HttpSession
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.springframework.http.HttpStatus

class AuthControllerTest {
    private val authService = mockk<AuthService>()
    private val authController = AuthController(authService)

    @Test
    fun `signup returns 200 OK`() =
        runBlocking {
            val request = SignupRequest("test@test.com", "password")

            coEvery { authService.signup(any()) } returns Unit

            val response = authController.signup(request)

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("success", response.body?.status)

            coVerify { authService.signup(request) }
        }

    @Test
    fun `signup propagates UnauthorizedException from service`() =
        runBlocking {
            val request = SignupRequest("existing@test.com", "password")

            coEvery { authService.signup(any()) } throws UnauthorizedException("Signup failed. Please check your credentials.")

            assertThrows<UnauthorizedException> {
                authController.signup(request)
            }
        }

    @Test
    fun `login returns 200 OK and creates session`() =
        runBlocking {
            val request = LoginRequest("test@test.com", "password")
            val httpSession = mockk<HttpSession>(relaxed = true)

            coEvery { authService.login(any()) } returns "fake-jwt"

            val response = authController.login(request, httpSession)

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("success", response.body?.status)

            coVerify { authService.login(request) }
            verify { httpSession.setAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE, "test@test.com") }
            verify { httpSession.setAttribute(SecurityConstants.SUPABASE_TOKEN_SESSION_ATTRIBUTE, "fake-jwt") }
            verify { httpSession.setAttribute(SecurityConstants.USER_ID_SESSION_ATTRIBUTE, "dummy_user_id_test@test.com") }
            verify { httpSession.setAttribute(SecurityConstants.BUSINESS_IDS_SESSION_ATTRIBUTE, emptyList<String>()) }
        }

    @Test
    fun `login propagates UnauthorizedException from service`() =
        runBlocking {
            val request = LoginRequest("bad@test.com", "wrong")
            val httpSession = mockk<HttpSession>(relaxed = true)

            coEvery { authService.login(any()) } throws UnauthorizedException("Invalid email or password.")

            assertThrows<UnauthorizedException> {
                authController.login(request, httpSession)
            }

            // Session should never have been modified
            verify(exactly = 0) { httpSession.setAttribute(any(), any()) }
        }

    @Test
    fun `me returns session email when logged in`() =
        runBlocking {
            val response = authController.me("test@test.com")

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("success", response.body?.status)
            assertEquals("test@test.com", response.body?.data?.email)
        }

    @Test
    fun `me throws UnauthorizedException when no session email`(): Unit =
        runBlocking {
            assertThrows<UnauthorizedException> {
                authController.me(null)
            }
        }

    @Test
    fun `logout invalidates existing session and returns 200`() {
        val httpSession = mockk<HttpSession>(relaxed = true)

        val response = authController.logout(httpSession)

        assertEquals(HttpStatus.OK, response.statusCode)
        assertEquals("success", response.body?.status)
        assertEquals("Logout successful", response.body?.message)
        verify { httpSession.invalidate() }
    }

    @Test
    fun `logout with no existing session still returns 200`() {
        val response = authController.logout(null)

        assertEquals(HttpStatus.OK, response.statusCode)
        assertEquals("success", response.body?.status)
        assertEquals("Logout successful", response.body?.message)
    }
}
