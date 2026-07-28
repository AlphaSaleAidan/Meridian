package com.meridian.unit.dto

import com.meridian.dto.ApiResponse
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test

class ApiResponseTest {
    @Test
    fun `success with defaults returns status success and code 200`() {
        val response = ApiResponse.success<Any>()

        assertEquals("success", response.status)
        assertEquals(200, response.code)
        assertEquals("Success", response.message)
        assertNull(response.data)
    }

    @Test
    fun `success with custom message and data`() {
        val response = ApiResponse.success(message = "Created", data = mapOf("id" to 42))

        assertEquals("success", response.status)
        assertEquals(200, response.code)
        assertEquals("Created", response.message)
        assertEquals(mapOf("id" to 42), response.data)
    }

    @Test
    fun `success with custom code`() {
        val response = ApiResponse.success<Any>(code = 201, message = "Resource created")

        assertEquals("success", response.status)
        assertEquals(201, response.code)
        assertEquals("Resource created", response.message)
    }

    @Test
    fun `error returns status error with correct code and message`() {
        val response = ApiResponse.error(404, "Not found")

        assertEquals("error", response.status)
        assertEquals(404, response.code)
        assertEquals("Not found", response.message)
        assertNull(response.data)
    }
}
