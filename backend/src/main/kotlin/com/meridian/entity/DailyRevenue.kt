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

/**
 * Grain of the `daily_revenue` materialized view: one row per org, location
 * and day. The view has no declared primary key, so the natural grain is the
 * entity id (verified unique and non-null in production).
 */
@Embeddable
data class DailyRevenueId(
    @Column(name = "org_id")
    val orgId: String,
    @Column(name = "location_id")
    val locationId: String,
    @Column(name = "day_bucket")
    val dayBucket: Instant,
) : Serializable

/** Read model over the `daily_revenue` materialized view. Never written by the app. */
@Entity
@Immutable
@Table(name = "daily_revenue")
class DailyRevenue(
    @EmbeddedId
    val id: DailyRevenueId,
    @Column(name = "transaction_count")
    val transactionCount: Long? = null,
    @Column(name = "total_revenue_cents")
    val totalRevenueCents: Long? = null,
    @Column(name = "refund_total_cents")
    val refundTotalCents: Long? = null,
    @Column(name = "refund_count")
    val refundCount: Long? = null,
    @Column(name = "avg_ticket_cents")
    val avgTicketCents: BigDecimal? = null,
    @Column(name = "total_tax_cents")
    val totalTaxCents: Long? = null,
    @Column(name = "total_tip_cents")
    val totalTipCents: Long? = null,
    @Column(name = "total_discount_cents")
    val totalDiscountCents: Long? = null,
    // Nullable in production: the view sums transactions.customer_count, which
    // no POS mapper currently writes. See AlphaSaleAidan/Meridian#425.
    @Column(name = "unique_customers")
    val uniqueCustomers: Long? = null,
)
