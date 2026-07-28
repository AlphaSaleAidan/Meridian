package com.meridian

import com.meridian.support.PostgresIntegrationTest
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import org.springframework.boot.test.context.SpringBootTest

@Tag("integration")
@SpringBootTest
class MeridianApplicationTests : PostgresIntegrationTest() {
    @Test
    fun contextLoads() {
    }
}
