package com.meridian.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.Table
import org.hibernate.annotations.Immutable
import java.time.Instant

/** Latest "Money Left on the Table" score for an org. Written by the AI pipeline, read-only here. */
@Entity
@Immutable
@Table(name = "money_left_scores")
class MoneyLeftScore(
    @Id
    val id: String,
    @Column(name = "org_id")
    val orgId: String? = null,
    @Column(name = "total_score_cents")
    val totalScoreCents: Long? = null,
    @Column(name = "scored_at")
    val scoredAt: Instant? = null,
    @Column(name = "model_version")
    val modelVersion: String? = null,
)
