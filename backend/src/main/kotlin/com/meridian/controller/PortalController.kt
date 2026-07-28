package com.meridian.controller

import com.meridian.dto.ApiResponse
import com.meridian.dto.GeneratePortalTokenRequest
import com.meridian.dto.PortalResolveResponse
import com.meridian.dto.PortalTokenResponse
import com.meridian.service.portal.PortalService
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.tags.Tag
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api/portal")
@Tag(
    name = "Portal",
    description =
        "Per-customer portal links. Every merchant gets an unguessable token stored in " +
            "businesses.access_token that powers their exclusive dashboard URL " +
            "(canada.meridian.tips/c/{token}) — no password required, the token IS the auth.",
)
class PortalController(
    private val portalService: PortalService,
    // JPA is blocking, so each service call runs on one virtual thread via
    // withContext — keeps @Transactional's ThreadLocal binding intact.
    private val virtualThreadDispatcher: CoroutineDispatcher,
) {
    @Operation(
        summary = "Resolve a portal token to org details",
        description =
            "Called by the SPA when a merchant opens their portal link (/c/{token}). Maps the token to " +
                "org id, business name, plan tier, POS provider and onboarding state so the dashboard can " +
                "render. Public by design — the unguessable token is the credential. 404 if the token is " +
                "unknown or the business is not active.",
    )
    @GetMapping("/resolve/{token}")
    suspend fun resolve(
        @PathVariable token: String,
    ): ResponseEntity<ApiResponse<PortalResolveResponse>> =
        withContext(virtualThreadDispatcher) {
            ResponseEntity.ok(ApiResponse.success(data = portalService.resolveToken(token)))
        }

    @Operation(
        summary = "Generate (or fetch) a merchant's portal token",
        description =
            "Used by the sales/onboarding flow to mint a customer's portal URL. Idempotent: returns the " +
                "existing token when one is set, otherwise issues a cryptographically random token, persists " +
                "it with token_status=pending, and returns the full portal URL. Requires an authenticated session.",
    )
    @PostMapping("/generate")
    suspend fun generate(
        @RequestBody request: GeneratePortalTokenRequest,
    ): ResponseEntity<ApiResponse<PortalTokenResponse>> =
        withContext(virtualThreadDispatcher) {
            ResponseEntity.ok(ApiResponse.success(data = portalService.generateToken(request)))
        }
}
