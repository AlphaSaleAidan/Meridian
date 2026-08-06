package com.meridian.integration

import com.meridian.support.PostgresIntegrationTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Tag
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.session.Session
import org.springframework.session.SessionRepository
import org.springframework.session.jdbc.JdbcIndexedSessionRepository
import java.nio.file.Files
import java.nio.file.Path
import javax.sql.DataSource

/**
 * Guards against sessions silently degrading to in-container (Tomcat memory) storage:
 * autowiring [JdbcIndexedSessionRepository] fails outright if spring-session-jdbc backed
 * off (e.g. the JDBC DataSource disappears again), and the round-trip proves the
 * scripts/sql/init-local-db.sql DDL matches what spring-session actually writes.
 */
@Tag("integration")
@SpringBootTest
class SessionPersistenceIntegrationTest : PostgresIntegrationTest() {
    @Autowired
    private lateinit var sessionRepository: JdbcIndexedSessionRepository

    @Autowired
    private lateinit var dataSource: DataSource

    @Test
    fun `sessions persist and load through spring-session-jdbc`() {
        // initialize-schema is "embedded", so apply the shared DDL exactly like local/prod do
        val ddl = Files.readString(Path.of("scripts/sql/init-local-db.sql"))
        dataSource.connection.use { connection ->
            connection.createStatement().use { it.execute(ddl) }
        }

        // JdbcSession is package-private, so interact through the public SessionRepository API
        @Suppress("UNCHECKED_CAST")
        val repository = sessionRepository as SessionRepository<Session>

        val session = repository.createSession()
        session.setAttribute("USER_EMAIL", "roundtrip@meridian.tips")
        repository.save(session)

        val loaded = repository.findById(session.id)

        assertNotNull(loaded)
        assertEquals("roundtrip@meridian.tips", loaded?.getAttribute("USER_EMAIL"))
    }
}
