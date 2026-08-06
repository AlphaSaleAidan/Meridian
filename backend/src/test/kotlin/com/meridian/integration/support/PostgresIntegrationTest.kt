package com.meridian.support

import org.springframework.test.context.DynamicPropertyRegistry
import org.springframework.test.context.DynamicPropertySource
import org.testcontainers.containers.PostgreSQLContainer

abstract class PostgresIntegrationTest {
    companion object {
        // Singleton container, started once for the whole test JVM (Ryuk reaps it at exit).
        // Deliberately NOT @Testcontainers/@Container: the extension stops a shared static
        // container after the first test class finishes, while Spring's cached application
        // contexts from that class keep pooling connections against the old mapped port —
        // every later class that reuses such a context then fails with "connection refused".
        val postgres =
            PostgreSQLContainer<Nothing>("postgres:15.1")
                .apply {
                    withDatabaseName("meridian_test")
                    withUsername("test")
                    withPassword("test")
                }.also { it.start() }

        @JvmStatic
        @DynamicPropertySource
        fun properties(registry: DynamicPropertyRegistry) {
            registry.add("spring.r2dbc.url") {
                "r2dbc:postgresql://${postgres.host}:${postgres.getMappedPort(5432)}/${postgres.databaseName}"
            }
            registry.add("spring.r2dbc.username", postgres::getUsername)
            registry.add("spring.r2dbc.password", postgres::getPassword)
            // JDBC DataSource for spring-session-jdbc — without these the context fails to
            // start now that a JDBC DataSource is required again.
            registry.add("spring.datasource.url", postgres::getJdbcUrl)
            registry.add("spring.datasource.username", postgres::getUsername)
            registry.add("spring.datasource.password", postgres::getPassword)
        }
    }
}
