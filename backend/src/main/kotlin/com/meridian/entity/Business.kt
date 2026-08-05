package com.meridian.entity

/**
 * Business data model mapped via raw SQL with DatabaseClient.
 */
data class Business(
    val id: String,
    val name: String? = null,
    val planTier: String? = null,
    val accessToken: String? = null,
    val tokenStatus: String? = null,
    val status: String? = null,
    val posProvider: String? = null,
    val onboarded: Boolean = false,
)
