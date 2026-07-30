package com.meridian.service.auth

import com.meridian.repository.OrgMembershipRepository
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service

/**
 * Access is granted when the session user is the org owner
 * (businesses.owner_user_id) or an active member (business_users), or when
 * their email is on the admin allowlist (meridian.auth.admin-emails —
 * internal ops/support accounts allowed to act on any org, port of the
 * FastAPI ADMIN_EMAILS bypass). The enforcement-disabled flag is an
 * emergency rollback knob: denials are logged but reported as allowed.
 *
 * Blocking membership queries run on the virtual-thread dispatcher so
 * suspend callers never block a servlet thread.
 */
@Service
class OrgAccessServiceImpl(
    private val orgMembershipRepository: OrgMembershipRepository,
    @Value("\${meridian.auth.admin-emails}") adminEmailsConfig: List<String>,
    @Value("\${meridian.auth.tenancy-enforcement-disabled}") private val enforcementDisabled: Boolean,
    private val virtualThreadDispatcher: CoroutineDispatcher,
) : OrgAccessService {
    private val log = LoggerFactory.getLogger(OrgAccessServiceImpl::class.java)
    private val adminEmails = adminEmailsConfig.map { it.trim().lowercase() }.filter { it.isNotEmpty() }.toSet()

    override suspend fun hasOrgAccess(
        userId: String?,
        email: String?,
        orgId: String,
    ): Boolean {
        if (email != null && email.lowercase() in adminEmails) {
            return true
        }
        if (userId.isNullOrBlank()) {
            log.warn("TENANCY_DENY (no session user) email={} tried org={}", email, orgId)
            return false
        }
        val isMember =
            withContext(virtualThreadDispatcher) {
                orgMembershipRepository.isOwner(orgId, userId) ||
                    orgMembershipRepository.isActiveMember(orgId, userId)
            }
        if (isMember) {
            return true
        }
        if (enforcementDisabled) {
            log.warn("TENANCY_WARN (enforcement disabled) user={} email={} tried org={}", userId, email, orgId)
            return true
        }
        log.warn("TENANCY_DENY user={} email={} tried org={}", userId, email, orgId)
        return false
    }
}
