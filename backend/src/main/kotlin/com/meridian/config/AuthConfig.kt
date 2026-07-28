package com.meridian.config

import com.meridian.service.auth.AuthService
import com.meridian.service.auth.SupabaseAuthServiceImpl
import io.ktor.client.HttpClient
import io.ktor.client.engine.apache5.Apache5
import org.springframework.beans.factory.annotation.Value
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import tools.jackson.databind.json.JsonMapper

@Configuration
class AuthConfig {
    @Bean
    fun ktorHttpClient(): HttpClient =
        HttpClient(Apache5) {
            expectSuccess = false
        }

    @Bean
    fun authService(
        @Value("\${supabase.url}") supabaseUrl: String,
        @Value("\${supabase.key}") supabaseKey: String,
        ktorHttpClient: HttpClient,
        jsonMapper: JsonMapper,
    ): AuthService =
        SupabaseAuthServiceImpl(
            supabaseUrl = supabaseUrl,
            supabaseKey = supabaseKey,
            httpClient = ktorHttpClient,
            jsonMapper = jsonMapper,
        )
}
