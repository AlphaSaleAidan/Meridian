package com.meridian.security

/**
 * Common session attribute keys used across AuthController and RequestContextFilter.
 */
object SecurityConstants {
    const val USER_ID_SESSION_ATTRIBUTE = "USER_ID"
    const val USER_EMAIL_SESSION_ATTRIBUTE = "USER_EMAIL"
    const val BUSINESS_IDS_SESSION_ATTRIBUTE = "BUSINESS_IDS"
    const val SUPABASE_TOKEN_SESSION_ATTRIBUTE = "SUPABASE_TOKEN"
}
