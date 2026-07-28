package com.meridian.controller

import com.meridian.dto.ApiResponse
import com.meridian.dto.HourlyRevenueResponse
import com.meridian.dto.OverviewResponse
import com.meridian.dto.RevenueResponse
import com.meridian.service.auth.OrgAccessService
import com.meridian.service.dashboard.DashboardService
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.tags.Tag
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.bind.annotation.SessionAttribute

@RestController
@RequestMapping("/api/dashboard")
@Tag(
    name = "Dashboard",
    description =
        "The merchant's home screen: revenue totals, trends and POS connection health. " +
            "Every endpoint is org-scoped and tenancy-guarded — the session user must own the org " +
            "or be an active member of it.",
)
class DashboardController(
    private val dashboardService: DashboardService,
    private val orgAccessService: OrgAccessService,
    // JPA is blocking; each call runs whole on one virtual thread so
    // @Transactional's ThreadLocal binding stays intact.
    private val virtualThreadDispatcher: CoroutineDispatcher,
) {
    @Operation(
        summary = "Headline metrics for the last 30 days",
        description =
            "Revenue, transaction count and average ticket for the trailing 30 days, the percentage " +
                "change against the prior 30, the latest Money Left on the Table score, and POS " +
                "connection status. This is the first call the dashboard makes after login.",
    )
    @GetMapping("/overview")
    suspend fun overview(
        @RequestParam orgId: String,
        @SessionAttribute(name = "SUPABASE_USER_ID", required = false) userId: String?,
        @SessionAttribute(name = "USER_EMAIL", required = false) email: String?,
    ): ResponseEntity<ApiResponse<OverviewResponse>> =
        withContext(virtualThreadDispatcher) {
            orgAccessService.requireOrgAccess(userId, email, orgId)
            ResponseEntity.ok(ApiResponse.success(data = dashboardService.getOverview(orgId)))
        }

    @Operation(
        summary = "Daily and weekly revenue series",
        description = "Powers the revenue charts. `days` accepts 7–365 and defaults to 30.",
    )
    @GetMapping("/revenue")
    suspend fun revenue(
        @RequestParam orgId: String,
        @RequestParam(defaultValue = "30") days: Long,
        @SessionAttribute(name = "SUPABASE_USER_ID", required = false) userId: String?,
        @SessionAttribute(name = "USER_EMAIL", required = false) email: String?,
    ): ResponseEntity<ApiResponse<RevenueResponse>> =
        withContext(virtualThreadDispatcher) {
            orgAccessService.requireOrgAccess(userId, email, orgId)
            ResponseEntity.ok(ApiResponse.success(data = dashboardService.getRevenue(orgId, days)))
        }

    @Operation(
        summary = "Hourly revenue breakdown",
        description =
            "Hour-by-hour revenue for the peak-hours heat map, including payment-method mix. " +
                "`days` accepts 7–90 and defaults to 30.",
    )
    @GetMapping("/revenue/hourly")
    suspend fun hourlyRevenue(
        @RequestParam orgId: String,
        @RequestParam(defaultValue = "30") days: Long,
        @SessionAttribute(name = "SUPABASE_USER_ID", required = false) userId: String?,
        @SessionAttribute(name = "USER_EMAIL", required = false) email: String?,
    ): ResponseEntity<ApiResponse<HourlyRevenueResponse>> =
        withContext(virtualThreadDispatcher) {
            orgAccessService.requireOrgAccess(userId, email, orgId)
            ResponseEntity.ok(ApiResponse.success(data = dashboardService.getHourlyRevenue(orgId, days)))
        }
}
