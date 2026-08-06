package com.meridian.security

import kotlinx.coroutines.ThreadContextElement
import kotlinx.coroutines.asContextElement

/**
 * Singleton holder for [RequestContext] backed by a [ThreadLocal].
 *
 * Provides thread-local storage for request identity and coroutine context propagation
 * across suspension points via [asCoroutineElement].
 *
 * WARNING: a plain [get]/[require] inside a suspend call chain is only safe BEFORE the first
 * suspension point — afterwards the coroutine resumes on another thread and reads null.
 * Propagation across suspension requires explicitly entering the coroutine context with
 * `withContext(RequestContextHolder.asCoroutineElement()) { ... }`; nothing does that
 * automatically. Suspend controllers should prefer a `RequestContext` handler parameter
 * (see [RequestContextArgumentResolver]) over this holder.
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
