package com.meridian.security

import kotlinx.coroutines.ThreadContextElement
import kotlinx.coroutines.asContextElement

/**
 * Singleton holder for [RequestContext] backed by a [ThreadLocal].
 *
 * Provides thread-local storage for request identity and coroutine context propagation
 * across suspension points via [asCoroutineElement].
 */
object RequestContextHolder {
    private val threadLocalContext = ThreadLocal<RequestContext?>()

    fun get(): RequestContext? = threadLocalContext.get()

    fun require(): RequestContext = get() ?: throw IllegalStateException("No RequestContext present on current thread")

    fun set(context: RequestContext) {
        threadLocalContext.set(context)
    }

    fun clear() {
        threadLocalContext.remove()
    }

    /**
     * Converts the ThreadLocal context into a [ThreadContextElement] for coroutines,
     * ensuring that coroutine suspension/resumption preserves [RequestContext] across threads.
     */
    fun asCoroutineElement(): ThreadContextElement<RequestContext?> = threadLocalContext.asContextElement()
}
