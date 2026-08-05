package com.meridian.security

/**
 * Thread-safe and coroutine-suspension-safe request context carrying user identity
 * and multi-tenant business access scoping.
 */
data class RequestContext(
    val userId: String,
    val userEmail: String,
    val businessIds: List<String> = emptyList(),
)
