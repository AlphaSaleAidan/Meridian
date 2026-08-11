package com.meridian.controller

import com.meridian.dto.ApiResponse
import com.meridian.dto.PendingBusinessResponse
import com.meridian.service.onboarding.OnboardingService
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.tags.Tag
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api/onboarding")
@Tag(
    name = "Onboarding",
    description =
        "Invite-token onboarding: a sales rep pre-creates the business and issues a token; the customer " +
            "validates it before signup and redeems it during signup (see POST /api/auth/signup).",
)
class OnboardingController(
    private val onboardingService: OnboardingService,
) {
    @Operation(
        summary = "Validate an invite token",
        description =
            "Public pre-signup check (the unguessable token IS the auth): returns the pending business's " +
                "name/owner for the \"you're joining X\" screen when the token is unredeemed and unexpired; " +
                "404 otherwise. Port of the validate_access_token RPC.",
    )
    @GetMapping("/token/{token}")
    suspend fun validateToken(
        @PathVariable token: String,
    ): ResponseEntity<ApiResponse<PendingBusinessResponse>> {
        val pending = onboardingService.validateToken(token)
        val response =
            PendingBusinessResponse(
                businessId = pending.businessId,
                businessName = pending.businessName,
                ownerName = pending.ownerName,
                email = pending.email,
                businessType = pending.businessType,
            )
        return ResponseEntity.ok(ApiResponse.success(data = response))
    }
}
