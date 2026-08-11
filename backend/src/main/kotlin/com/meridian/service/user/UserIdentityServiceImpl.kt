package com.meridian.service.user

import com.meridian.repository.AdminUserRepository
import com.meridian.repository.BusinessRepository
import com.meridian.repository.BusinessUserRepository
import com.meridian.repository.SalesRepRepository
import org.springframework.stereotype.Service

@Service
class UserIdentityServiceImpl(
    private val businessRepository: BusinessRepository,
    private val businessUserRepository: BusinessUserRepository,
    private val adminUserRepository: AdminUserRepository,
    private val salesRepRepository: SalesRepRepository,
) : UserIdentityService {
    override suspend fun resolveIdentity(
        userId: String,
        email: String,
        displayName: String?,
        isVerified: Boolean,
    ): UserIdentity {
        val owned =
            businessRepository.findByOwnerUserId(userId).map { business ->
                UserBusiness(businessId = business.id, businessName = business.name, role = ROLE_OWNER)
            }
        val ownedIds = owned.map { it.businessId }.toSet()
        val memberships =
            businessUserRepository
                .findActiveMembershipsByUserId(userId)
                // An owner may also have a business_users row; ownership wins.
                .filterNot { it.businessId in ownedIds }
                .map { membership ->
                    UserBusiness(
                        businessId = membership.businessId,
                        businessName = membership.businessName,
                        role = membership.role,
                        locationId = membership.locationId,
                    )
                }

        val businesses = owned + memberships
        val primary = businesses.firstOrNull()

        return UserIdentity(
            userId = userId,
            email = email,
            displayName = displayName,
            role = primary?.role ?: ROLE_STAFF,
            orgId = primary?.businessId,
            locationId = primary?.locationId,
            isVerified = isVerified,
            isAdmin = adminUserRepository.existsByUserId(userId),
            isSalesRep = salesRepRepository.existsActiveByEmail(email),
            businesses = businesses,
        )
    }

    override suspend fun recordLogin(userId: String) {
        businessUserRepository.recordLogin(userId)
    }

    companion object {
        private const val ROLE_OWNER = "owner"
        private const val ROLE_STAFF = "staff"
    }
}
