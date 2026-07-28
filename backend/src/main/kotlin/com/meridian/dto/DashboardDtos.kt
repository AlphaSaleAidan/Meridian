package com.meridian.dto

import java.time.Instant

data class ConnectionStatus(
    val status: String,
    val provider: String?,
    val lastSyncAt: Instant?,
)

data class MoneyLeftSummary(
    val totalScoreCents: Long?,
    val scoredAt: Instant?,
    val modelVersion: String?,
)

data class OverviewResponse(
    val revenueCents30d: Long,
    val revenueChangePct: Double,
    val transactionCount30d: Long,
    val avgTicketCents: Long,
    val moneyLeftScore: MoneyLeftSummary?,
    val connection: ConnectionStatus,
    val daysWithData: Int,
)

data class DailyRevenuePoint(
    val date: Instant,
    val revenueCents: Long,
    val transactions: Long,
    val avgTicketCents: Long,
    val refundCents: Long,
    val taxCents: Long,
    val tipCents: Long,
    val discountCents: Long,
    val customers: Long,
)

data class WeeklyRevenuePoint(
    val week: Instant,
    val revenueCents: Long,
    val transactions: Long,
    val avgTicketCents: Long,
)

data class RevenueResponse(
    val daily: List<DailyRevenuePoint>,
    val weekly: List<WeeklyRevenuePoint>,
)

data class HourlyRevenuePoint(
    val hour: Instant,
    val revenueCents: Long,
    val sales: Long,
    val refunds: Long,
    val avgTicketCents: Long,
    val customers: Long,
    val cashCount: Long,
    val creditCount: Long,
)

data class HourlyRevenueResponse(
    val hourly: List<HourlyRevenuePoint>,
)
