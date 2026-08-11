package com.meridian.unit.controller

import com.meridian.controller.AuthController
import com.meridian.dto.ChangePasswordRequest
import com.meridian.dto.ForgotPasswordRequest
import com.meridian.dto.LoginRequest
import com.meridian.dto.ResetPasswordRequest
import com.meridian.dto.SignupRequest
import com.meridian.exception.UnauthorizedException
import com.meridian.security.SecurityConstants
import com.meridian.service.auth.AuthService
import com.meridian.service.auth.SupabaseSession
import com.meridian.service.auth.SupabaseUser
import com.meridian.service.auth.SupabaseUserMetadata
import com.meridian.service.user.UserBusiness
import com.meridian.service.user.UserIdentity
import com.meridian.service.user.UserIdentityService
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
import java.util.UUID

class AuthControllerTest {
    private val authService = mockk<AuthService>()
    private val userIdentityService = mockk<UserIdentityService>()
    private val authController = AuthController(authService, userIdentityService)

    private val supabaseUser =
        SupabaseUser(
            id = "00000000-0000-0000-0000-000000000001",
            email = "test@test.com",
            emailConfirmedAt = "2026-08-11T00:00:00Z",
            userMetadata = SupabaseUserMetadata(displayName = "Test Owner"),
        )

    private val identity =
        UserIdentity(
            userId = UUID.fromString("00000000-0000-0000-0000-000000000001"),
            email = "test@test.com",
            displayName = "Test Owner",
            role = "owner",
            orgId = "biz_1",
            isVerified = true,
            isAdmin = false,
            isSalesRep = false,
            businesses = listOf(UserBusiness(businessId = "biz_1", businessName = "Test Biz", role = "owner")),
        )

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
    fun `login returns 200 OK and stores resolved identity in session`() =
        runBlocking {
            val request = LoginRequest("test@test.com", "password")
            val httpSession = mockk<HttpSession>(relaxed = true)

            coEvery { authService.login(any()) } returns SupabaseSession(accessToken = "fake-jwt", user = supabaseUser)
            coEvery {
                userIdentityService.resolveIdentity(
                    userId = UUID.fromString("00000000-0000-0000-0000-000000000001"),
                    email = "test@test.com",
                    displayName = "Test Owner",
                    isVerified = true,
                )
            } returns identity
            coEvery { userIdentityService.recordLogin(UUID.fromString("00000000-0000-0000-0000-000000000001")) } returns Unit

            val response = authController.login(request, httpSession)

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("success", response.body?.status)

            coVerify { authService.login(request) }
            coVerify { userIdentityService.recordLogin(UUID.fromString("00000000-0000-0000-0000-000000000001")) }
            verify { httpSession.setAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE, "test@test.com") }
            verify { httpSession.setAttribute(SecurityConstants.SUPABASE_TOKEN_SESSION_ATTRIBUTE, "fake-jwt") }
            verify { httpSession.setAttribute(SecurityConstants.USER_ID_SESSION_ATTRIBUTE, "00000000-0000-0000-0000-000000000001") }
            verify { httpSession.setAttribute(SecurityConstants.BUSINESS_IDS_SESSION_ATTRIBUTE, arrayListOf("biz_1")) }
            verify { httpSession.setAttribute(SecurityConstants.USER_IDENTITY_SESSION_ATTRIBUTE, identity) }
        }

    @Test
    fun `login falls back to request email when Supabase omits it`() =
        runBlocking {
            val request = LoginRequest("fallback@test.com", "password")
            val httpSession = mockk<HttpSession>(relaxed = true)
            val userWithoutEmail = supabaseUser.copy(email = null, userMetadata = null)

            coEvery { authService.login(any()) } returns SupabaseSession(accessToken = "fake-jwt", user = userWithoutEmail)
            coEvery {
                userIdentityService.resolveIdentity(
                    userId = UUID.fromString("00000000-0000-0000-0000-000000000001"),
                    email = "fallback@test.com",
                    displayName = null,
                    isVerified = true,
                )
            } returns identity.copy(email = "fallback@test.com")
            coEvery { userIdentityService.recordLogin(UUID.fromString("00000000-0000-0000-0000-000000000001")) } returns Unit

            val response = authController.login(request, httpSession)

            assertEquals(HttpStatus.OK, response.statusCode)
            verify { httpSession.setAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE, "fallback@test.com") }
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
    fun `me returns full session identity when logged in`() =
        runBlocking {
            val response = authController.me(identity)

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("success", response.body?.status)
            val data = response.body?.data
            assertEquals("00000000-0000-0000-0000-000000000001", data?.id)
            assertEquals("test@test.com", data?.email)
            assertEquals("Test Owner", data?.displayName)
            assertEquals("owner", data?.role)
            assertEquals("biz_1", data?.orgId)
            assertEquals(true, data?.isVerified)
            assertEquals(false, data?.isAdmin)
            assertEquals(false, data?.isSalesRep)
            assertEquals(1, data?.businesses?.size)
            assertEquals("biz_1", data?.businesses?.first()?.businessId)
            assertEquals("Test Biz", data?.businesses?.first()?.businessName)
        }

    @Test
    fun `me throws UnauthorizedException when no session identity`(): Unit =
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

    @Test
    fun `forgot-password always returns the generic success message`() =
        runBlocking {
            coEvery { authService.forgotPassword("someone@test.com") } returns Unit

            val response = authController.forgotPassword(ForgotPasswordRequest("someone@test.com"))

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("If the email exists, a reset link has been sent", response.body?.message)
            coVerify { authService.forgotPassword("someone@test.com") }
        }

    @Test
    fun `reset-password delegates recovery token and new password`() =
        runBlocking {
            coEvery { authService.resetPassword("recovery-tok", "new-pass-123") } returns Unit

            val response = authController.resetPassword(ResetPasswordRequest("recovery-tok", "new-pass-123"))

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("Password updated", response.body?.message)
            coVerify { authService.resetPassword("recovery-tok", "new-pass-123") }
        }

    @Test
    fun `change-password verifies the current password and uses the fresh token`() =
        runBlocking {
            val httpSession = mockk<HttpSession>(relaxed = true)
            coEvery {
                authService.login(LoginRequest("test@test.com", "current-pass"))
            } returns SupabaseSession(accessToken = "fresh-jwt", user = supabaseUser)
            coEvery { authService.changePassword("fresh-jwt", "new-pass-123") } returns Unit

            val response =
                authController.changePassword(
                    ChangePasswordRequest("current-pass", "new-pass-123"),
                    "test@test.com",
                    httpSession,
                )

            assertEquals(HttpStatus.OK, response.statusCode)
            assertEquals("Password updated", response.body?.message)
            coVerify { authService.changePassword("fresh-jwt", "new-pass-123") }
            verify { httpSession.setAttribute(SecurityConstants.SUPABASE_TOKEN_SESSION_ATTRIBUTE, "fresh-jwt") }
        }

    @Test
    fun `change-password rejects a wrong current password`(): Unit =
        runBlocking {
            val httpSession = mockk<HttpSession>(relaxed = true)
            coEvery { authService.login(any()) } throws UnauthorizedException("Invalid email or password.")

            val exception =
                assertThrows<UnauthorizedException> {
                    authController.changePassword(
                        ChangePasswordRequest("wrong-pass", "new-pass-123"),
                        "test@test.com",
                        httpSession,
                    )
                }
            assertEquals("Current password is incorrect", exception.message)
        }

    @Test
    fun `change-password throws UnauthorizedException without a session`(): Unit =
        runBlocking {
            val httpSession = mockk<HttpSession>(relaxed = true)
            assertThrows<UnauthorizedException> {
                authController.changePassword(
                    ChangePasswordRequest("current-pass", "new-pass-123"),
                    null,
                    httpSession,
                )
            }
        }
}
