package com.meridian.repository.jdbc

import com.meridian.repository.OrgMembershipRepository
import org.springframework.jdbc.core.simple.JdbcClient
import org.springframework.stereotype.Repository

@Repository
class JdbcOrgMembershipRepository(
    private val jdbcClient: JdbcClient,
) : OrgMembershipRepository {
    override fun isOwner(
        orgId: String,
        userId: String,
    ): Boolean =
        jdbcClient
            .sql("SELECT EXISTS (SELECT 1 FROM businesses WHERE id = :orgId AND owner_user_id = :userId)")
            .param("orgId", orgId)
            .param("userId", userId)
            .query(Boolean::class.javaObjectType)
            .single()

    override fun isActiveMember(
        orgId: String,
        userId: String,
    ): Boolean =
        jdbcClient
            .sql("SELECT EXISTS (SELECT 1 FROM business_users WHERE business_id = :orgId AND user_id = :userId AND is_active)")
            .param("orgId", orgId)
            .param("userId", userId)
            .query(Boolean::class.javaObjectType)
            .single()
}
