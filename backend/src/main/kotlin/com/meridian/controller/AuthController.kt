package com.meridian.controller

import com.meridian.dto.ApiResponse
import com.meridian.dto.LoginRequest
import com.meridian.dto.SessionInfoResponse
import com.meridian.dto.SignupRequest
import com.meridian.exception.UnauthorizedException
import com.meridian.service.auth.AuthService
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.tags.Tag
import jakarta.servlet.http.HttpSession
import org.slf4j.LoggerFactory
import org.springframework.http.ResponseEntity
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken
import org.springframework.security.core.context.SecurityContextHolder
import org.springframework.security.web.context.HttpSessionSecurityContextRepository
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.bind.annotation.SessionAttribute

@RestController
@RequestMapping("/api/auth")
@Tag(
    name = "Auth",
    description =
        "Merchant signup, login/logout and session identity. Credentials are verified against " +
            "Supabase Auth; the backend then owns the session via JDBC-backed cookies (spring-session), " +
            "so the SPA never handles JWTs directly.",
)
class AuthController(
    private val authService: AuthService,
) {
    private val log = LoggerFactory.getLogger(AuthController::class.java)

    @Operation(
        summary = "Create a merchant account",
        description = "Registers the email/password with Supabase Auth. The user logs in separately once confirmed.",
    )
    @PostMapping("/signup")
    suspend fun signup(
        @RequestBody request: SignupRequest,
    ): ResponseEntity<ApiResponse<Any>> {
        authService.signup(request)
        return ResponseEntity.ok(ApiResponse.success(message = "Signup successful"))
    }

    @Operation(
        summary = "Log in and start a session",
        description =
            "Verifies credentials with Supabase Auth, then creates a JDBC-backed cookie session holding " +
                "the user email and Supabase access token. All protected endpoints authenticate via this session.",
    )
    @PostMapping("/login")
    suspend fun login(
        @RequestBody request: LoginRequest,
        session: HttpSession,
    ): ResponseEntity<ApiResponse<Any>> {
        val supabaseToken = authService.login(request)

        // Inform Spring Security that the user is authenticated
        val auth = UsernamePasswordAuthenticationToken(request.email, null, emptyList())
        val securityContext = SecurityContextHolder.createEmptyContext()
        securityContext.authentication = auth
        SecurityContextHolder.setContext(securityContext)

        // Save the context to the session so it persists across requests
        session.setAttribute(HttpSessionSecurityContextRepository.SPRING_SECURITY_CONTEXT_KEY, securityContext)
        session.setAttribute("USER_EMAIL", request.email)
        session.setAttribute("SUPABASE_TOKEN", supabaseToken)

        log.info("Created backend JDBC session for: {}", request.email)

        return ResponseEntity.ok(ApiResponse.success(message = "Login successful"))
    }

    @Operation(
        summary = "Who is logged in",
        description =
            "Returns the current session's user identity. The SPA calls this on load to decide between " +
                "the logged-in dashboard and the login screen — with cookie sessions it has no JWT to decode. " +
                "401 when there is no active session.",
    )
    @GetMapping("/me")
    suspend fun me(
        @SessionAttribute(name = "USER_EMAIL", required = false) email: String?,
    ): ResponseEntity<ApiResponse<SessionInfoResponse>> {
        if (email == null) {
            throw UnauthorizedException("Not authenticated")
        }
        return ResponseEntity.ok(ApiResponse.success(data = SessionInfoResponse(email = email)))
    }

    @Operation(
        summary = "Log out",
        description = "Invalidates the JDBC session and clears the security context. Safe to call without a session.",
    )
    @PostMapping("/logout")
    fun logout(session: HttpSession?): ResponseEntity<ApiResponse<Any>> {
        SecurityContextHolder.clearContext()
        if (session != null) {
            session.invalidate()
            log.info("Invalidated JDBC session")
        }
        return ResponseEntity.ok(ApiResponse.success(message = "Logout successful"))
    }
}
