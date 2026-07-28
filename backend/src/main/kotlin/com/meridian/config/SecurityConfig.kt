package com.meridian.config

import jakarta.servlet.FilterChain
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.security.config.annotation.web.builders.HttpSecurity
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity
import org.springframework.security.config.http.SessionCreationPolicy
import org.springframework.security.core.userdetails.UserDetailsService
import org.springframework.security.core.userdetails.UsernameNotFoundException
import org.springframework.security.web.SecurityFilterChain
import org.springframework.security.web.authentication.www.BasicAuthenticationFilter
import org.springframework.security.web.csrf.CookieCsrfTokenRepository
import org.springframework.security.web.csrf.CsrfToken
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler
import org.springframework.web.filter.OncePerRequestFilter

@Configuration
@EnableWebSecurity
class SecurityConfig {
    @Bean
    fun filterChain(
        http: HttpSecurity,
        @Value("\${security.csrf.enabled:true}") csrfEnabled: Boolean,
    ): SecurityFilterChain {
        http
            .csrf { csrf ->
                if (csrfEnabled) {
                    // Enable CSRF using a cookie token repository (ideal for SPAs/frontend clients)
                    csrf.csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
                    // Use standard handler to avoid XorCsrfTokenRequestAttributeHandler issues with SPAs
                    csrf.csrfTokenRequestHandler(CsrfTokenRequestAttributeHandler())
                    // Ignore CSRF for auth endpoints so users can log in without a token
                    csrf.ignoringRequestMatchers("/api/auth/**")
                } else {
                    csrf.disable() // Used for local dev / testing
                }
            }.authorizeHttpRequests { auth ->
                auth.requestMatchers("/api/auth/**", "/v3/api-docs/**", "/swagger-ui/**").permitAll()
                // Portal resolve is public by design — the unguessable token IS the auth
                auth.requestMatchers("/api/portal/resolve/**").permitAll()
                auth.anyRequest().authenticated()
            }.sessionManagement { session ->
                session.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED)
            }.addFilterAfter(CsrfCookieFilter(), BasicAuthenticationFilter::class.java)

        return http.build()
    }

    /**
     * Enterprise pattern: By defining our own UserDetailsService bean, Spring Boot's
     * UserDetailsServiceAutoConfiguration completely backs off. This prevents Spring from
     * generating the annoying random password on startup. We throw an exception here
     * because we use Supabase for auth, not Spring's internal database/in-memory users.
     */
    @Bean
    fun userDetailsService(): UserDetailsService =
        UserDetailsService { _ ->
            throw UsernameNotFoundException("Internal Spring user lookup is disabled. We use Supabase.")
        }
}

/**
 * Spring Security 6 defers loading the CSRF token until it's explicitly accessed.
 * This filter forces the token to load, ensuring the XSRF-TOKEN cookie is sent to the frontend SPA.
 */
class CsrfCookieFilter : OncePerRequestFilter() {
    override fun doFilterInternal(
        request: HttpServletRequest,
        response: HttpServletResponse,
        filterChain: FilterChain,
    ) {
        val csrfToken = request.getAttribute(CsrfToken::class.java.name) as CsrfToken?
        // Render the token value to a cookie by causing the deferred token to be loaded
        csrfToken?.token
        filterChain.doFilter(request, response)
    }
}
