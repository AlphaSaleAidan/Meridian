package com.meridian.controller

import com.meridian.dto.HealthResponse
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.tags.Tag
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api")
@Tag(name = "Health", description = "Service liveness for load balancers and uptime checks.")
class HealthController {
    @Operation(
        summary = "Service health",
        description = "Returns healthy when the app is up. Session-protected like all non-auth endpoints.",
    )
    @GetMapping("/health")
    fun health(): HealthResponse =
        HealthResponse(
            status = "healthy",
            service = "meridian-kt",
        )
}
