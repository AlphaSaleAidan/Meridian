package com.meridian.entity

import jakarta.persistence.Column
import jakarta.persistence.Embeddable
import jakarta.persistence.EmbeddedId
import jakarta.persistence.Entity
import jakarta.persistence.Table
import org.hibernate.annotations.Immutable
import java.io.Serializable
import java.math.BigDecimal
import java.time.Instant

@Embeddable
data class WeeklyRevenueId(
    @Column(name = "org_id")
    val orgId: String,
    @Column(name = "location_id")
    val locationId: String,
    @Column(name = "week_bucket")
    val weekBucket: Instant,
) : Serializable

/** Read model over the `weekly_revenue` materialized view. */
@Entity
@Immutable
@Table(name = "weekly_revenue")
class WeeklyRevenue(
    @EmbeddedId
    val id: WeeklyRevenueId,
    @Column(name = "transaction_count")
    val transactionCount: Long? = null,
    @Column(name = "total_revenue_cents")
    val totalRevenueCents: Long? = null,
    @Column(name = "avg_ticket_cents")
    val avgTicketCents: BigDecimal? = null,
)
