package com.meridian.config

import com.zaxxer.hikari.HikariDataSource
import io.r2dbc.spi.ConnectionFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Primary
import org.springframework.jdbc.support.JdbcTransactionManager
import org.springframework.r2dbc.connection.R2dbcTransactionManager
import org.springframework.transaction.PlatformTransactionManager
import org.springframework.transaction.ReactiveTransactionManager
import javax.sql.DataSource

/**
 * R2DBC (DatabaseClient) is the application's data-access path; a JDBC DataSource coexists
 * solely so spring-session-jdbc can persist HTTP sessions.
 *
 * Everything here must be declared explicitly: Boot's DataSourceAutoConfiguration backs off
 * whenever an R2DBC ConnectionFactory is present (even with spring.datasource.* set), and the
 * single-manager transaction auto-configurations would otherwise register only one manager.
 * @Primary on the reactive manager is what `@Transactional` suspend service methods resolve
 * to; spring-session wires the platform manager by type.
 */
@Configuration
class PersistenceConfig {
    /** JDBC pool for spring-session-jdbc only — application queries go through R2DBC. */
    @Bean
    fun sessionDataSource(
        @Value("\${spring.datasource.url}") url: String,
        @Value("\${spring.datasource.username}") username: String,
        @Value("\${spring.datasource.password}") password: String,
    ): DataSource =
        HikariDataSource().apply {
            jdbcUrl = url
            this.username = username
            this.password = password
            poolName = "session-jdbc"
            maximumPoolSize = 5
        }

    @Bean
    @Primary
    fun r2dbcTransactionManager(connectionFactory: ConnectionFactory): ReactiveTransactionManager =
        R2dbcTransactionManager(connectionFactory)

    @Bean
    fun jdbcTransactionManager(dataSource: DataSource): PlatformTransactionManager = JdbcTransactionManager(dataSource)
}
