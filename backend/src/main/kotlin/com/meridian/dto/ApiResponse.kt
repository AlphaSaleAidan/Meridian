package com.meridian.dto

import com.fasterxml.jackson.annotation.JsonInclude

@JsonInclude(JsonInclude.Include.NON_NULL)
data class ApiResponse<T>(
    val status: String,
    val code: Int,
    val message: String,
    val data: T? = null,
) {
    companion object {
        fun <T> success(
            code: Int = 200,
            message: String = "Success",
            data: T? = null,
        ): ApiResponse<T> = ApiResponse("success", code, message, data)

        fun error(
            code: Int,
            message: String,
        ): ApiResponse<Any> = ApiResponse("error", code, message, null)
    }
}
