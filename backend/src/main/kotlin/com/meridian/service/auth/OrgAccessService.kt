package com.meridian.service.auth

import com.meridian.exception.ForbiddenException
import com.meridian.exception.UnauthorizedException
import com.meridian.repository.BusinessRepository
import com.meridian.repository.BusinessUserRepository
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional

/**
 * Tenancy guard for org-scoped endpoints (port of require_org_access).
 *
 * Access is granted when the session user is the org owner
 * (businesses.owner_user_id), an active member (business_users), or on the
 * admin allowlist. The enforcement-disabled flag is an emergency rollback
 * knob: denials are logged but allowed through.
 */
@Service
class OrgAccessService(
    private val businessRepository: BusinessRepository,
    private val businessUserRepository: BusinessUserRepository,
    @Value("\${meridian.auth.admin-emails}") adminEmailsConfig: List<String>,
    @Value("\${meridian.auth.tenancy-enforcement-disabled}") private val enforcementDisabled: Boolean,
) {
    private val log = LoggerFactory.getLogger(OrgAccessService::class.java)
    private val adminEmails = adminEmailsConfig.map { it.trim().lowercase() }.filter { it.isNotEmpty() }.toSet()

    @Transactional(readOnly = true)
    fun requireOrgAccess(
        userId: String?,
        email: String?,
        orgId: String,
    ) {
        if (email != null && email.lowercase() in adminEmails) {
            return
        }
        if (userId.isNullOrBlank()) {
            throw UnauthorizedException("Not authenticated")
        }
        if (businessRepository.existsByIdAndOwnerUserId(orgId, userId)) {
            return
        }
        if (businessUserRepository.existsByBusinessIdAndUserIdAndIsActiveTrue(orgId, userId)) {
            return
        }
        if (enforcementDisabled) {
            log.warn("TENANCY_WARN (enforcement disabled) user={} email={} tried org={}", userId, email, orgId)
            return
        }
        log.warn("TENANCY_DENY user={} email={} tried org={}", userId, email, orgId)
        throw ForbiddenException("You do not have access to this organization")
    }
}
