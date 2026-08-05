package com.meridian.unit.security

import com.meridian.security.RequestContext
import com.meridian.security.RequestContextHolder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withContext
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class RequestContextTest {
    @AfterEach
    fun tearDown() {
        RequestContextHolder.clear()
    }

    @Test
    fun `set and get request context on current thread`() {
        val context = RequestContext(userId = "usr_123", userEmail = "dev@meridian.tips", businessIds = listOf("biz_999"))
        RequestContextHolder.set(context)

        assertEquals(context, RequestContextHolder.get())
        assertEquals(context, RequestContextHolder.require())
    }

    @Test
    fun `require throws IllegalStateException when context is not set`() {
        assertThrows<IllegalStateException> {
            RequestContextHolder.require()
        }
    }

    @Test
    fun `clear removes request context from current thread`() {
        val context = RequestContext(userId = "usr_123", userEmail = "dev@meridian.tips")
        RequestContextHolder.set(context)
        RequestContextHolder.clear()

        assertNull(RequestContextHolder.get())
    }

    @Test
    fun `asCoroutineElement preserves context across thread context switching`() =
        runTest {
            val context = RequestContext(userId = "usr_123", userEmail = "dev@meridian.tips", businessIds = listOf("biz_1", "biz_2"))
            RequestContextHolder.set(context)

            withContext(Dispatchers.Default + RequestContextHolder.asCoroutineElement()) {
                assertEquals("usr_123", RequestContextHolder.require().userId)
                assertEquals("dev@meridian.tips", RequestContextHolder.require().userEmail)
                assertEquals(listOf("biz_1", "biz_2"), RequestContextHolder.require().businessIds)
            }
        }

    @Test
    fun `asCoroutineElement preserves context across multiple distinct dedicated threads`() =
        runTest {
            val initialThreadName = Thread.currentThread().name
            val context = RequestContext(userId = "usr_switch_888", userEmail = "switch@meridian.tips", businessIds = listOf("biz_a"))
            RequestContextHolder.set(context)

            val customExecutor1 =
                java.util.concurrent.Executors
                    .newSingleThreadExecutor { runnable ->
                        Thread(runnable, "custom-worker-thread-1")
                    }.asCoroutineDispatcher()

            val customExecutor2 =
                java.util.concurrent.Executors
                    .newSingleThreadExecutor { runnable ->
                        Thread(runnable, "custom-worker-thread-2")
                    }.asCoroutineDispatcher()

            try {
                // Hop to Thread 1
                withContext(customExecutor1 + RequestContextHolder.asCoroutineElement()) {
                    assertEquals("custom-worker-thread-1", Thread.currentThread().name)
                    assertNotEquals(initialThreadName, Thread.currentThread().name)
                    assertEquals("usr_switch_888", RequestContextHolder.require().userId)
                    assertEquals("switch@meridian.tips", RequestContextHolder.require().userEmail)
                    assertEquals(listOf("biz_a"), RequestContextHolder.require().businessIds)

                    // Hop to Thread 2 nested inside Thread 1
                    withContext(customExecutor2 + RequestContextHolder.asCoroutineElement()) {
                        assertEquals("custom-worker-thread-2", Thread.currentThread().name)
                        assertEquals("usr_switch_888", RequestContextHolder.require().userId)
                        assertEquals("switch@meridian.tips", RequestContextHolder.require().userEmail)
                        assertEquals(listOf("biz_a"), RequestContextHolder.require().businessIds)
                    }

                    // Resumed on Thread 1
                    assertEquals("custom-worker-thread-1", Thread.currentThread().name)
                    assertEquals("usr_switch_888", RequestContextHolder.require().userId)
                    assertEquals("switch@meridian.tips", RequestContextHolder.require().userEmail)
                    assertEquals(listOf("biz_a"), RequestContextHolder.require().businessIds)
                }
            } finally {
                customExecutor1.close()
                customExecutor2.close()
            }
        }
}
