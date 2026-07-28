package com.meridian.service.dashboard

import com.meridian.dto.ConnectionStatus
import com.meridian.dto.DailyRevenuePoint
import com.meridian.dto.HourlyRevenuePoint
import com.meridian.dto.HourlyRevenueResponse
import com.meridian.dto.MoneyLeftSummary
import com.meridian.dto.OverviewResponse
import com.meridian.dto.RevenueResponse
import com.meridian.dto.WeeklyRevenuePoint
import com.meridian.entity.DailyRevenue
import com.meridian.exception.BadRequestException
import com.meridian.repository.DailyRevenueRepository
import com.meridian.repository.HourlyRevenueRepository
import com.meridian.repository.MoneyLeftScoreRepository
import com.meridian.repository.PosConnectionRepository
import com.meridian.repository.WeeklyRevenueRepository
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.math.BigDecimal
import java.math.RoundingMode
import java.time.Clock
import java.time.Duration
import java.time.Instant

/**
 * Dashboard analytics — the numbers behind the merchant's home screen.
 *
 * Reads the revenue materialized views; all figures are in cents.
 */
@Service
class DashboardService(
    private val dailyRevenueRepository: DailyRevenueRepository,
    private val weeklyRevenueRepository: WeeklyRevenueRepository,
    private val hourlyRevenueRepository: HourlyRevenueRepository,
    private val moneyLeftScoreRepository: MoneyLeftScoreRepository,
    private val posConnectionRepository: PosConnectionRepository,
    private val clock: Clock,
) {
    @Transactional(readOnly = true)
    fun getOverview(orgId: String): OverviewResponse {
        val now = clock.instant()
        val cutoff = now.minus(Duration.ofDays(OVERVIEW_WINDOW_DAYS))
        val windowStart = now.minus(Duration.ofDays(OVERVIEW_WINDOW_DAYS * 2))

        val rows =
            dailyRevenueRepository
                .findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(orgId, windowStart)

        val (current, prior) = rows.partition { !it.id.dayBucket.isBefore(cutoff) }

        val currentRevenue = current.sumOfCents { it.totalRevenueCents }
        val priorRevenue = prior.sumOfCents { it.totalRevenueCents }
        val currentTxns = current.sumOfCents { it.transactionCount }

        val connection = posConnectionRepository.findFirstByOrgIdOrderByLastSyncAtDesc(orgId)
        val moneyLeft = moneyLeftScoreRepository.findFirstByOrgIdOrderByScoredAtDesc(orgId)

        return OverviewResponse(
            revenueCents30d = currentRevenue,
            revenueChangePct = percentChange(from = priorRevenue, to = currentRevenue),
            transactionCount30d = currentTxns,
            avgTicketCents = if (currentTxns > 0) currentRevenue / currentTxns else 0,
            moneyLeftScore =
                moneyLeft?.let {
                    MoneyLeftSummary(
                        totalScoreCents = it.totalScoreCents,
                        scoredAt = it.scoredAt,
                        modelVersion = it.modelVersion,
                    )
                },
            connection =
                ConnectionStatus(
                    status = connection?.status ?: DISCONNECTED,
                    provider = connection?.provider,
                    lastSyncAt = connection?.lastSyncAt,
                ),
            daysWithData = current.size,
        )
    }

    @Transactional(readOnly = true)
    fun getRevenue(
        orgId: String,
        days: Long,
    ): RevenueResponse {
        val since = sinceOrThrow(days, maxDays = MAX_REVENUE_DAYS)

        val daily = dailyRevenueRepository.findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(orgId, since)
        val weekly = weeklyRevenueRepository.findByIdOrgIdAndIdWeekBucketGreaterThanEqualOrderByIdWeekBucketAsc(orgId, since)

        return RevenueResponse(
            daily =
                daily.map {
                    DailyRevenuePoint(
                        date = it.id.dayBucket,
                        revenueCents = it.totalRevenueCents.orZero(),
                        transactions = it.transactionCount.orZero(),
                        avgTicketCents = it.avgTicketCents.toCents(),
                        refundCents = it.refundTotalCents.orZero(),
                        taxCents = it.totalTaxCents.orZero(),
                        tipCents = it.totalTipCents.orZero(),
                        discountCents = it.totalDiscountCents.orZero(),
                        customers = it.uniqueCustomers.orZero(),
                    )
                },
            weekly =
                weekly.map {
                    WeeklyRevenuePoint(
                        week = it.id.weekBucket,
                        revenueCents = it.totalRevenueCents.orZero(),
                        transactions = it.transactionCount.orZero(),
                        avgTicketCents = it.avgTicketCents.toCents(),
                    )
                },
        )
    }

    @Transactional(readOnly = true)
    fun getHourlyRevenue(
        orgId: String,
        days: Long,
    ): HourlyRevenueResponse {
        val since = sinceOrThrow(days, maxDays = MAX_HOURLY_DAYS)

        val hourly = hourlyRevenueRepository.findByIdOrgIdAndIdHourBucketGreaterThanEqualOrderByIdHourBucketAsc(orgId, since)

        return HourlyRevenueResponse(
            hourly =
                hourly.map {
                    HourlyRevenuePoint(
                        hour = it.id.hourBucket,
                        revenueCents = it.totalRevenueCents.orZero(),
                        sales = it.saleCount.orZero(),
                        refunds = it.refundCount.orZero(),
                        avgTicketCents = it.avgTicketCents.toCents(),
                        customers = it.uniqueCustomers.orZero(),
                        cashCount = it.cashCount.orZero(),
                        creditCount = it.creditCount.orZero(),
                    )
                },
        )
    }

    private fun sinceOrThrow(
        days: Long,
        maxDays: Long,
    ): Instant {
        if (days < MIN_DAYS || days > maxDays) {
            throw BadRequestException("days must be between $MIN_DAYS and $maxDays")
        }
        return clock.instant().minus(Duration.ofDays(days))
    }

    private fun percentChange(
        from: Long,
        to: Long,
    ): Double {
        if (from <= 0) return 0.0
        return BigDecimal
            .valueOf(to - from)
            .divide(BigDecimal.valueOf(from), PERCENT_SCALE, RoundingMode.HALF_UP)
            .multiply(BigDecimal.valueOf(100))
            .setScale(1, RoundingMode.HALF_UP)
            .toDouble()
    }

    private fun Long?.orZero(): Long = this ?: 0

    private fun BigDecimal?.toCents(): Long = this?.setScale(0, RoundingMode.HALF_UP)?.toLong() ?: 0

    private fun List<DailyRevenue>.sumOfCents(selector: (DailyRevenue) -> Long?): Long = sumOf { selector(it) ?: 0 }

    companion object {
        private const val OVERVIEW_WINDOW_DAYS = 30L
        private const val MIN_DAYS = 7L
        private const val MAX_REVENUE_DAYS = 365L
        private const val MAX_HOURLY_DAYS = 90L
        private const val PERCENT_SCALE = 6
        private const val DISCONNECTED = "disconnected"
    }
}
