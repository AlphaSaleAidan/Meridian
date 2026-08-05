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
        // Configure specific URL patterns where RequestContext binding is active (e.g. "/api/v1/*")
        // Currently no endpoints require scoped context binding yet, so urlPatterns is empty for now.
        registration.urlPatterns = emptyList()
        return registration
    }
}
