package com.meridian

import com.meridian.support.PostgresIntegrationTest
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.r2dbc.core.DatabaseClient
import org.springframework.r2dbc.core.awaitOneOrNull

@Tag("integration")
@SpringBootTest
class DatabaseIntegrationTest : PostgresIntegrationTest() {
    @Autowired
    private lateinit var databaseClient: DatabaseClient

    @Test
    fun `context loads and database connects`() =
        runTest {
            val result: Int? =
                databaseClient
                    .sql("SELECT 1 AS num")
                    .map { row, _ -> row.get("num", Int::class.javaObjectType) ?: 0 }
                    .awaitOneOrNull()

            assertEquals(1, result)
        }
}
