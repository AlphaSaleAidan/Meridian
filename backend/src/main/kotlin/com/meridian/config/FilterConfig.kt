package com.meridian.config

import com.meridian.security.MeridianRequestContextFilter
import org.springframework.boot.web.servlet.FilterRegistrationBean
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

/**
 * Configuration for servlet filter registrations and URL pattern scoping.
 */
@Configuration
class FilterConfig {
    @Bean
    fun meridianRequestContextFilterRegistration(
        filter: MeridianRequestContextFilter,
    ): FilterRegistrationBean<MeridianRequestContextFilter> {
        val registration = FilterRegistrationBean(filter)
        // No endpoint consumes the ThreadLocal context yet, so the registration is disabled.
        // NOTE: an empty urlPatterns list does NOT disable a filter — Spring Boot falls back
        // to mapping "/*" when no patterns are given. Set enabled=true and add real patterns
        // (e.g. "/api/v1/*") once a non-suspend consumer of RequestContextHolder exists;
        // suspend handlers should use a RequestContext parameter instead (see
        // RequestContextArgumentResolver).
        registration.setEnabled(false)
        return registration
    }
}
