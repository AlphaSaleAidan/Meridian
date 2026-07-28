package com.meridian.entity

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.Table
import java.time.Instant

/**
 * A merchant's POS integration. Only the non-sensitive status columns are
 * mapped — encrypted tokens and credentials are deliberately left off this
 * entity so they cannot leak into a dashboard response.
 */
@Entity
@Table(name = "pos_connections")
class PosConnection(
    @Id
    val id: String,
    @Column(name = "org_id")
    val orgId: String? = null,
    @Column(name = "provider")
    val provider: String? = null,
    @Column(name = "status")
    val status: String? = null,
    @Column(name = "last_sync_at")
    val lastSyncAt: Instant? = null,
    @Column(name = "last_sync_status")
    val lastSyncStatus: String? = null,
)
