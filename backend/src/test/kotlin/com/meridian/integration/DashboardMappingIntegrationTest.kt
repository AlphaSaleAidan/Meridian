package com.meridian.integration

import com.meridian.repository.DailyRevenueRepository
import com.meridian.repository.HourlyRevenueRepository
import com.meridian.repository.MoneyLeftScoreRepository
import com.meridian.repository.PosConnectionRepository
import com.meridian.repository.WeeklyRevenueRepository
import com.meridian.support.PostgresIntegrationTest
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.jdbc.core.JdbcTemplate
import java.time.Instant
import java.time.temporal.ChronoUnit

/**
 * Proves the dashboard read models map cleanly onto the real column layout of
 * the revenue views. The app never writes these views, so the fixtures create
 * plain tables with the production column names — a mapping mistake (wrong
 * column, wrong type, incomplete composite key) fails here rather than in prod.
 */
@Tag("integration")
@SpringBootTest
class DashboardMappingIntegrationTest : PostgresIntegrationTest() {
    @Autowired private lateinit var jdbcTemplate: JdbcTemplate

    @Autowired private lateinit var dailyRevenueRepository: DailyRevenueRepository

    @Autowired private lateinit var weeklyRevenueRepository: WeeklyRevenueRepository

    @Autowired private lateinit var hourlyRevenueRepository: HourlyRevenueRepository

    @Autowired private lateinit var moneyLeftScoreRepository: MoneyLeftScoreRepository

    @Autowired private lateinit var posConnectionRepository: PosConnectionRepository

    private val orgId = "org-int-1"
    private val since: Instant = Instant.now().minus(90, ChronoUnit.DAYS)

    @BeforeEach
    fun seed() {
        jdbcTemplate.execute("TRUNCATE daily_revenue, weekly_revenue, hourly_revenue, money_left_scores, pos_connections")

        jdbcTemplate.update(
            """
            INSERT INTO daily_revenue (org_id, location_id, day_bucket, transaction_count, total_revenue_cents,
                refund_total_cents, refund_count, avg_ticket_cents, total_tax_cents, total_tip_cents,
                total_discount_cents, unique_customers)
            VALUES (?, 'loc-1', now() - interval '2 days', 4, 4000, 0, 0, 1000.0, 100, 50, 0, NULL)
            """.trimIndent(),
            orgId,
        )
        jdbcTemplate.update(
            """
            INSERT INTO weekly_revenue (org_id, location_id, week_bucket, transaction_count, total_revenue_cents, avg_ticket_cents)
            VALUES (?, 'loc-1', now() - interval '3 days', 10, 10000, 1000.0)
            """.trimIndent(),
            orgId,
        )
        jdbcTemplate.update(
            """
            INSERT INTO hourly_revenue (org_id, location_id, hour_bucket, sale_count, refund_count, void_count,
                total_revenue_cents, avg_ticket_cents, unique_customers, cash_count, credit_count, debit_count, mobile_count)
            VALUES (?, 'loc-1', now() - interval '5 hours', 3, 1, 0, 3000, 1000.0, NULL, 1, 2, 0, 0)
            """.trimIndent(),
            orgId,
        )
        jdbcTemplate.update(
            """
            INSERT INTO money_left_scores (id, org_id, total_score_cents, scored_at, model_version)
            VALUES ('mls-1', ?, 4200, now(), 'v2')
            """.trimIndent(),
            orgId,
        )
        jdbcTemplate.update(
            """
            INSERT INTO pos_connections (id, org_id, provider, status, last_sync_at, last_sync_status)
            VALUES ('pc-1', ?, 'square', 'connected', now(), 'ok')
            """.trimIndent(),
            orgId,
        )
    }

    @Test
    fun `daily revenue maps and tolerates a null unique_customers`() {
        val rows = dailyRevenueRepository.findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(orgId, since)

        assertTrue(rows.size == 1)
        val row = rows.first()
        assertTrue(row.id.orgId == orgId)
        assertTrue(row.totalRevenueCents == 4000L)
        assertTrue(row.transactionCount == 4L)
        // NULL in production — must not blow up the mapping
        assertTrue(row.uniqueCustomers == null)
    }

    @Test
    fun `weekly and hourly revenue map onto their real columns`() {
        val weekly = weeklyRevenueRepository.findByIdOrgIdAndIdWeekBucketGreaterThanEqualOrderByIdWeekBucketAsc(orgId, since)
        val hourly = hourlyRevenueRepository.findByIdOrgIdAndIdHourBucketGreaterThanEqualOrderByIdHourBucketAsc(orgId, since)

        assertTrue(weekly.size == 1)
        assertTrue(weekly.first().totalRevenueCents == 10000L)

        assertTrue(hourly.size == 1)
        val hour = hourly.first()
        assertTrue(hour.saleCount == 3L)
        assertTrue(hour.refundCount == 1L)
        assertTrue(hour.cashCount == 1L)
        assertTrue(hour.creditCount == 2L)
    }

    @Test
    fun `latest money-left score and pos connection resolve for the org`() {
        assertTrue(moneyLeftScoreRepository.findFirstByOrgIdOrderByScoredAtDesc(orgId)?.totalScoreCents == 4200L)
        assertTrue(posConnectionRepository.findFirstByOrgIdOrderByLastSyncAtDesc(orgId)?.provider == "square")
    }
}
