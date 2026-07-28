package com.meridian.unit.exception

import com.meridian.exception.BadRequestException
import com.meridian.exception.GlobalExceptionHandler
import com.meridian.exception.NotFoundException
import com.meridian.exception.UnauthorizedException
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.springframework.http.HttpStatus

class GlobalExceptionHandlerTest {
    private val handler = GlobalExceptionHandler()

    @Test
    fun `handleUnauthorizedException returns 401 with error ApiResponse`() {
        val exception = UnauthorizedException("Invalid credentials")

        val response = handler.handleUnauthorizedException(exception)

        assertEquals(HttpStatus.UNAUTHORIZED, response.statusCode)
        assertEquals("error", response.body?.status)
        assertEquals(401, response.body?.code)
        assertEquals("Invalid credentials", response.body?.message)
    }

    @Test
    fun `handleBadRequestException returns 400 with error ApiResponse`() {
        val exception = BadRequestException("Missing email field")

        val response = handler.handleBadRequestException(exception)

        assertEquals(HttpStatus.BAD_REQUEST, response.statusCode)
        assertEquals("error", response.body?.status)
        assertEquals(400, response.body?.code)
        assertEquals("Missing email field", response.body?.message)
    }

    @Test
    fun `handleNotFoundException returns 404 with error ApiResponse`() {
        val exception = NotFoundException("Business not found")

        val response = handler.handleNotFoundException(exception)

        assertEquals(HttpStatus.NOT_FOUND, response.statusCode)
        assertEquals("error", response.body?.status)
        assertEquals(404, response.body?.code)
        assertEquals("Business not found", response.body?.message)
    }

    @Test
    fun `handleGenericException returns 500 and does not leak internal details`() {
        val exception = RuntimeException("NullPointerException in some deep stack")

        val response = handler.handleGenericException(exception)

        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.statusCode)
        assertEquals("error", response.body?.status)
        assertEquals(500, response.body?.code)
        assertEquals("An unexpected error occurred.", response.body?.message)
    }
}
