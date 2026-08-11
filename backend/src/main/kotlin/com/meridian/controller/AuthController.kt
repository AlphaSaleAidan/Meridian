package com.meridian.controller

import com.meridian.dto.ApiResponse
import com.meridian.dto.ChangePasswordRequest
import com.meridian.dto.ForgotPasswordRequest
import com.meridian.dto.LoginRequest
import com.meridian.dto.ResetPasswordRequest
import com.meridian.dto.SessionBusinessResponse
import com.meridian.dto.SessionInfoResponse
import com.meridian.dto.SignupRequest
import com.meridian.exception.UnauthorizedException
import com.meridian.security.SecurityConstants
import com.meridian.service.auth.AuthService
import com.meridian.service.user.UserIdentity
import com.meridian.service.user.UserIdentityService
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
import java.util.UUID

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
    private val userIdentityService: UserIdentityService,
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
        val supabaseSession = authService.login(request)
        val supabaseUser = supabaseSession.user
        val email = supabaseUser.email ?: request.email
        // Boundary parse: Supabase ids are uuids; a malformed one means a broken upstream, not a bad login.
        val userId = UUID.fromString(supabaseUser.id)
        val identity =
            userIdentityService.resolveIdentity(
                userId = userId,
                email = email,
                displayName = supabaseUser.userMetadata?.displayName ?: supabaseUser.userMetadata?.fullName,
                isVerified = supabaseUser.emailConfirmedAt != null,
            )
        userIdentityService.recordLogin(identity.userId)

        // Inform Spring Security that the user is authenticated
        val auth = UsernamePasswordAuthenticationToken(email, null, emptyList())
        val securityContext = SecurityContextHolder.createEmptyContext()
        securityContext.authentication = auth
        SecurityContextHolder.setContext(securityContext)

        // Save the context to the session so it persists across requests
        session.setAttribute(HttpSessionSecurityContextRepository.SPRING_SECURITY_CONTEXT_KEY, securityContext)
        session.setAttribute(SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE, email)
        session.setAttribute(SecurityConstants.SUPABASE_TOKEN_SESSION_ATTRIBUTE, supabaseSession.accessToken)
        session.setAttribute(SecurityConstants.USER_ID_SESSION_ATTRIBUTE, identity.userId.toString())
        session.setAttribute(
            SecurityConstants.BUSINESS_IDS_SESSION_ATTRIBUTE,
            ArrayList(identity.businesses.map { it.businessId }),
        )
        session.setAttribute(SecurityConstants.USER_IDENTITY_SESSION_ATTRIBUTE, identity)

        log.info("Created backend JDBC session for: {} ({} businesses)", email, identity.businesses.size)

        return ResponseEntity.ok(ApiResponse.success(message = "Login successful"))
    }

    @Operation(
        summary = "Request a password-reset email",
        description =
            "Triggers Supabase's recovery email. Always answers with the same generic success whether or " +
                "not the email exists (anti-enumeration); infrastructure failures (Supabase SMTP rate cap, " +
                "5xx) are logged for ops but never exposed to the caller.",
    )
    @PostMapping("/forgot-password")
    suspend fun forgotPassword(
        @RequestBody request: ForgotPasswordRequest,
    ): ResponseEntity<ApiResponse<Any>> {
        authService.forgotPassword(request.email)
        return ResponseEntity.ok(ApiResponse.success(message = "If the email exists, a reset link has been sent"))
    }

    @Operation(
        summary = "Reset password from an email link",
        description =
            "Completes the recovery flow: the SPA reads the recovery access token from the reset link's " +
                "URL fragment and posts it here with the new password. This is the one flow where the SPA " +
                "handles a raw Supabase token — the fragment never reaches the backend otherwise. " +
                "No session is created; the user logs in afterwards.",
    )
    @PostMapping("/reset-password")
    suspend fun resetPassword(
        @RequestBody request: ResetPasswordRequest,
    ): ResponseEntity<ApiResponse<Any>> {
        authService.resetPassword(request.accessToken, request.newPassword)
        return ResponseEntity.ok(ApiResponse.success(message = "Password updated"))
    }

    @Operation(
        summary = "Change password while logged in",
        description =
            "Session-authenticated password change (settings page). Requires the current password, which is " +
                "verified via a fresh Supabase password grant — the session's stored access token may have " +
                "expired (sessions outlive Supabase tokens and no refresh token is kept), and requiring the " +
                "current password also stops a hijacked session from silently changing it. Distinct from " +
                "reset-password, which uses a recovery token. 401 when there is no active session.",
    )
    @PostMapping("/change-password")
    suspend fun changePassword(
        @RequestBody request: ChangePasswordRequest,
        @SessionAttribute(
            name = SecurityConstants.USER_EMAIL_SESSION_ATTRIBUTE,
            required = false,
        ) email: String?,
        session: HttpSession,
    ): ResponseEntity<ApiResponse<Any>> {
        if (email == null) {
            throw UnauthorizedException("Not authenticated")
        }
        val freshSession =
            try {
                authService.login(LoginRequest(email = email, password = request.currentPassword))
            } catch (e: UnauthorizedException) {
                throw UnauthorizedException("Current password is incorrect")
            }
        authService.changePassword(freshSession.accessToken, request.newPassword)
        // Keep the session's stored token current for any later Supabase-proxied calls
        session.setAttribute(SecurityConstants.SUPABASE_TOKEN_SESSION_ATTRIBUTE, freshSession.accessToken)
        return ResponseEntity.ok(ApiResponse.success(message = "Password updated"))
    }

    @Operation(
        summary = "Who is logged in",
        description =
            "Returns the current session's resolved identity: profile, table-derived role, admin/sales-rep " +
                "flags and business memberships. The SPA calls this on load to decide between the logged-in " +
                "dashboard and the login screen — with cookie sessions it has no JWT to decode. It also " +
                "replaces the SPA's direct is_admin RPC, sales_reps and businesses lookups. " +
                "401 when there is no active session.",
    )
    @GetMapping("/me")
    suspend fun me(
        @SessionAttribute(
            name = SecurityConstants.USER_IDENTITY_SESSION_ATTRIBUTE,
            required = false,
        ) identity: UserIdentity?,
    ): ResponseEntity<ApiResponse<SessionInfoResponse>> {
        if (identity == null) {
            throw UnauthorizedException("Not authenticated")
        }
        val response =
            SessionInfoResponse(
                id = identity.userId.toString(),
                email = identity.email,
                displayName = identity.displayName,
                role = identity.role,
                orgId = identity.orgId,
                locationId = identity.locationId,
                isVerified = identity.isVerified,
                isAdmin = identity.isAdmin,
                isSalesRep = identity.isSalesRep,
                businesses =
                    identity.businesses.map { business ->
                        SessionBusinessResponse(
                            businessId = business.businessId,
                            businessName = business.businessName,
                            role = business.role,
                            locationId = business.locationId,
                        )
                    },
            )
        return ResponseEntity.ok(ApiResponse.success(data = response))
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
