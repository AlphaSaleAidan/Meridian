package com.meridian.config

import org.springframework.context.annotation.Configuration
import org.springframework.web.servlet.config.annotation.InterceptorRegistry
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer

@Configuration
class WebConfig : WebMvcConfigurer {
    override fun addInterceptors(registry: InterceptorRegistry) {
        // You can register your custom interceptors here in the future!
        // e.g., registry.addInterceptor(LoggingInterceptor()).addPathPatterns("/api/**")
    }
}
