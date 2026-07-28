package com.meridian.unit.service.dashboard

import com.meridian.entity.DailyRevenue
import com.meridian.entity.DailyRevenueId
import com.meridian.entity.HourlyRevenue
import com.meridian.entity.HourlyRevenueId
import com.meridian.entity.MoneyLeftScore
import com.meridian.entity.PosConnection
import com.meridian.exception.BadRequestException
import com.meridian.repository.DailyRevenueRepository
import com.meridian.repository.HourlyRevenueRepository
import com.meridian.repository.MoneyLeftScoreRepository
import com.meridian.repository.PosConnectionRepository
import com.meridian.repository.WeeklyRevenueRepository
import com.meridian.service.dashboard.DashboardService
import io.mockk.every
import io.mockk.mockk
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.math.BigDecimal
import java.time.Clock
import java.time.Duration
import java.time.Instant
import java.time.ZoneOffset

class DashboardServiceTest {
    private val dailyRepo = mockk<DailyRevenueRepository>()
    private val weeklyRepo = mockk<WeeklyRevenueRepository>(relaxed = true)
    private val hourlyRepo = mockk<HourlyRevenueRepository>()
    private val moneyLeftRepo = mockk<MoneyLeftScoreRepository>()
    private val posRepo = mockk<PosConnectionRepository>()

    private val now: Instant = Instant.parse("2026-07-28T12:00:00Z")
    private val clock: Clock = Clock.fixed(now, ZoneOffset.UTC)

    private val service =
        DashboardService(dailyRepo, weeklyRepo, hourlyRepo, moneyLeftRepo, posRepo, clock)

    private val orgId = "org-1"

    private fun daily(
        daysAgo: Long,
        revenue: Long?,
        txns: Long? = 1,
        customers: Long? = null,
    ) = DailyRevenue(
        id = DailyRevenueId(orgId, "loc-1", now.minus(Duration.ofDays(daysAgo))),
        transactionCount = txns,
        totalRevenueCents = revenue,
        uniqueCustomers = customers,
        avgTicketCents = BigDecimal("100.5"),
    )

    // ---- overview ----

    @Test
    fun `overview splits the window into current and prior 30 days`() {
        every { dailyRepo.findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(orgId, any()) } returns
            listOf(
                daily(daysAgo = 5, revenue = 1000, txns = 4),
                daily(daysAgo = 10, revenue = 1000, txns = 6),
                // prior period
                daily(daysAgo = 40, revenue = 800, txns = 3),
                daily(daysAgo = 50, revenue = 200, txns = 2),
            )
        every { moneyLeftRepo.findFirstByOrgIdOrderByScoredAtDesc(orgId) } returns null
        every { posRepo.findFirstByOrgIdOrderByLastSyncAtDesc(orgId) } returns null

        val result = service.getOverview(orgId)

        assertEquals(2000, result.revenueCents30d)
        assertEquals(10, result.transactionCount30d)
        assertEquals(200, result.avgTicketCents)
        assertEquals(2, result.daysWithData)
        // prior 1000 → current 2000 = +100%
        assertEquals(100.0, result.revenueChangePct)
    }

    @Test
    fun `overview reports zero change when there is no prior revenue`() {
        every { dailyRepo.findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(orgId, any()) } returns
            listOf(daily(daysAgo = 3, revenue = 500))
        every { moneyLeftRepo.findFirstByOrgIdOrderByScoredAtDesc(orgId) } returns null
        every { posRepo.findFirstByOrgIdOrderByLastSyncAtDesc(orgId) } returns null

        val result = service.getOverview(orgId)

        assertEquals(0.0, result.revenueChangePct)
        assertEquals(500, result.revenueCents30d)
    }

    @Test
    fun `overview tolerates null revenue and zero transactions`() {
        every { dailyRepo.findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(orgId, any()) } returns
            listOf(daily(daysAgo = 2, revenue = null, txns = null))
        every { moneyLeftRepo.findFirstByOrgIdOrderByScoredAtDesc(orgId) } returns null
        every { posRepo.findFirstByOrgIdOrderByLastSyncAtDesc(orgId) } returns null

        val result = service.getOverview(orgId)

        assertEquals(0, result.revenueCents30d)
        assertEquals(0, result.transactionCount30d)
        // must not divide by zero
        assertEquals(0, result.avgTicketCents)
    }

    @Test
    fun `overview reports disconnected when the org has no POS connection`() {
        every { dailyRepo.findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(orgId, any()) } returns emptyList()
        every { moneyLeftRepo.findFirstByOrgIdOrderByScoredAtDesc(orgId) } returns null
        every { posRepo.findFirstByOrgIdOrderByLastSyncAtDesc(orgId) } returns null

        val result = service.getOverview(orgId)

        assertEquals("disconnected", result.connection.status)
        assertNull(result.connection.provider)
        assertNull(result.moneyLeftScore)
    }

    @Test
    fun `overview surfaces connection and money-left details when present`() {
        val scoredAt = now.minus(Duration.ofDays(1))
        every { dailyRepo.findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(orgId, any()) } returns emptyList()
        every { moneyLeftRepo.findFirstByOrgIdOrderByScoredAtDesc(orgId) } returns
            MoneyLeftScore(id = "s1", orgId = orgId, totalScoreCents = 4200, scoredAt = scoredAt, modelVersion = "v2")
        every { posRepo.findFirstByOrgIdOrderByLastSyncAtDesc(orgId) } returns
            PosConnection(id = "c1", orgId = orgId, provider = "square", status = "connected", lastSyncAt = scoredAt)

        val result = service.getOverview(orgId)

        assertEquals("connected", result.connection.status)
        assertEquals("square", result.connection.provider)
        assertEquals(4200, result.moneyLeftScore?.totalScoreCents)
        assertEquals("v2", result.moneyLeftScore?.modelVersion)
    }

    // ---- revenue ----

    @Test
    fun `revenue maps rows and defaults null customers to zero`() {
        every { dailyRepo.findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(orgId, any()) } returns
            listOf(daily(daysAgo = 1, revenue = 900, txns = 3, customers = null))
        every { weeklyRepo.findByIdOrgIdAndIdWeekBucketGreaterThanEqualOrderByIdWeekBucketAsc(orgId, any()) } returns emptyList()

        val result = service.getRevenue(orgId, days = 30)

        assertEquals(1, result.daily.size)
        assertEquals(900, result.daily[0].revenueCents)
        assertEquals(0, result.daily[0].customers)
        // BigDecimal 100.5 rounds half-up to 101 cents
        assertEquals(101, result.daily[0].avgTicketCents)
    }

    @Test
    fun `revenue rejects a days value outside the allowed range`() {
        assertThrows<BadRequestException> { service.getRevenue(orgId, days = 3) }
        assertThrows<BadRequestException> { service.getRevenue(orgId, days = 400) }
    }

    // ---- hourly ----

    @Test
    fun `hourly maps payment mix and rejects windows over 90 days`() {
        every { hourlyRepo.findByIdOrgIdAndIdHourBucketGreaterThanEqualOrderByIdHourBucketAsc(orgId, any()) } returns
            listOf(
                HourlyRevenue(
                    id = HourlyRevenueId(orgId, "loc-1", now.minus(Duration.ofHours(2))),
                    saleCount = 5,
                    refundCount = 1,
                    totalRevenueCents = 2500,
                    avgTicketCents = BigDecimal("500"),
                    cashCount = 2,
                    creditCount = 3,
                ),
            )

        val result = service.getHourlyRevenue(orgId, days = 30)

        assertEquals(1, result.hourly.size)
        assertEquals(5, result.hourly[0].sales)
        assertEquals(1, result.hourly[0].refunds)
        assertEquals(2, result.hourly[0].cashCount)
        assertEquals(3, result.hourly[0].creditCount)
        assertEquals(2500, result.hourly[0].revenueCents)

        assertThrows<BadRequestException> { service.getHourlyRevenue(orgId, days = 91) }
    }
}
