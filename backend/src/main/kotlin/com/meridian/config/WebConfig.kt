package com.meridian.config

import com.meridian.security.RequestContextArgumentResolver
import org.springframework.context.annotation.Configuration
import org.springframework.web.method.support.HandlerMethodArgumentResolver
import org.springframework.web.servlet.config.annotation.InterceptorRegistry
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer

@Configuration
class WebConfig : WebMvcConfigurer {
    override fun addArgumentResolvers(resolvers: MutableList<HandlerMethodArgumentResolver>) {
        // Lets controllers declare a RequestContext parameter resolved from the session —
        // the suspension-safe alternative to reading RequestContextHolder's ThreadLocal.
        resolvers.add(RequestContextArgumentResolver())
    }

    override fun addInterceptors(registry: InterceptorRegistry) {
        // You can register your custom interceptors here in the future!
        // e.g., registry.addInterceptor(LoggingInterceptor()).addPathPatterns("/api/**")
    }
}
