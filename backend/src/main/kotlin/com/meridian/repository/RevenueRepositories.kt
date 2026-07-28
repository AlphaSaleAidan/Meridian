package com.meridian.repository

import com.meridian.entity.DailyRevenue
import com.meridian.entity.DailyRevenueId
import com.meridian.entity.HourlyRevenue
import com.meridian.entity.HourlyRevenueId
import com.meridian.entity.MoneyLeftScore
import com.meridian.entity.PosConnection
import com.meridian.entity.WeeklyRevenue
import com.meridian.entity.WeeklyRevenueId
import org.springframework.data.jpa.repository.JpaRepository
import java.time.Instant

interface DailyRevenueRepository : JpaRepository<DailyRevenue, DailyRevenueId> {
    fun findByIdOrgIdAndIdDayBucketGreaterThanEqualOrderByIdDayBucketAsc(
        orgId: String,
        since: Instant,
    ): List<DailyRevenue>
}

interface WeeklyRevenueRepository : JpaRepository<WeeklyRevenue, WeeklyRevenueId> {
    fun findByIdOrgIdAndIdWeekBucketGreaterThanEqualOrderByIdWeekBucketAsc(
        orgId: String,
        since: Instant,
    ): List<WeeklyRevenue>
}

interface HourlyRevenueRepository : JpaRepository<HourlyRevenue, HourlyRevenueId> {
    fun findByIdOrgIdAndIdHourBucketGreaterThanEqualOrderByIdHourBucketAsc(
        orgId: String,
        since: Instant,
    ): List<HourlyRevenue>
}

interface MoneyLeftScoreRepository : JpaRepository<MoneyLeftScore, String> {
    fun findFirstByOrgIdOrderByScoredAtDesc(orgId: String): MoneyLeftScore?
}

interface PosConnectionRepository : JpaRepository<PosConnection, String> {
    fun findFirstByOrgIdOrderByLastSyncAtDesc(orgId: String): PosConnection?
}
