package com.meridian

import com.meridian.support.PostgresIntegrationTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import javax.sql.DataSource

@Tag("integration")
@SpringBootTest
class DatabaseIntegrationTest : PostgresIntegrationTest() {
    @Autowired
    private lateinit var dataSource: DataSource

    @Test
    fun `context loads and database connects`() {
        dataSource.connection.use { connection ->
            val result = connection.createStatement().executeQuery("SELECT 1")
            result.next()
            assertEquals(1, result.getInt(1))
        }
    }
}
