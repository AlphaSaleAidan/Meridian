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
data class HourlyRevenueId(
    @Column(name = "org_id")
    val orgId: String,
    @Column(name = "location_id")
    val locationId: String,
    @Column(name = "hour_bucket")
    val hourBucket: Instant,
) : Serializable

/**
 * Read model over the `hourly_revenue` materialized view (heat map / peak hours).
 *
 * Note there is no `transaction_count` on this view — sales, refunds and voids
 * are counted separately.
 */
@Entity
@Immutable
@Table(name = "hourly_revenue")
class HourlyRevenue(
    @EmbeddedId
    val id: HourlyRevenueId,
    @Column(name = "sale_count")
    val saleCount: Long? = null,
    @Column(name = "refund_count")
    val refundCount: Long? = null,
    @Column(name = "void_count")
    val voidCount: Long? = null,
    @Column(name = "total_revenue_cents")
    val totalRevenueCents: Long? = null,
    @Column(name = "avg_ticket_cents")
    val avgTicketCents: BigDecimal? = null,
    @Column(name = "unique_customers")
    val uniqueCustomers: Long? = null,
    @Column(name = "cash_count")
    val cashCount: Long? = null,
    @Column(name = "credit_count")
    val creditCount: Long? = null,
    @Column(name = "debit_count")
    val debitCount: Long? = null,
    @Column(name = "mobile_count")
    val mobileCount: Long? = null,
)
