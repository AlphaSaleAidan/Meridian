package com.meridian.exception

open class BaseException(
    message: String,
) : RuntimeException(message)

class UnauthorizedException(
    message: String,
) : BaseException(message)

class BadRequestException(
    message: String,
) : BaseException(message)

class NotFoundException(
    message: String,
) : BaseException(message)
