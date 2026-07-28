package com.meridian.config

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.asCoroutineDispatcher
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import java.time.Clock
import java.util.concurrent.Executors

@Configuration
class CoroutinesConfig {
    /**
     * Dispatcher for calling blocking (JPA/JDBC) code from suspend handlers.
     * Each coroutine block runs entirely on one virtual thread, which keeps
     * Spring's ThreadLocal-bound @Transactional semantics intact while the
     * servlet thread stays free.
     */
    @Bean
    fun virtualThreadDispatcher(): CoroutineDispatcher = Executors.newVirtualThreadPerTaskExecutor().asCoroutineDispatcher()

    /** Injected rather than calling Instant.now() inline, so time windows are testable. */
    @Bean
    fun clock(): Clock = Clock.systemUTC()
}
