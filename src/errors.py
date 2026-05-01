"""
Meridian Error Hierarchy — Typed exceptions for structured error handling.

Usage:
    from src.errors import DataError, IntegrationError, AuthError

    raise DataError("No revenue data for org", org_id=org_id, days=30)
    raise IntegrationError("Square API timeout", provider="square", status=504)
    raise AuthError("Token expired", org_id=org_id)
"""


class MeridianError(Exception):
    """Base exception for all Meridian errors."""

    def __init__(self, message: str, **context):
        self.context = context
        super().__init__(message)

    def __str__(self):
        base = super().__str__()
        if self.context:
            ctx = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base} [{ctx}]"
        return base


class DataError(MeridianError):
    """Raised when required data is missing, invalid, or insufficient."""
    pass


class IntegrationError(MeridianError):
    """Raised when a POS or external service interaction fails."""
    pass


class AuthError(MeridianError):
    """Raised for authentication/authorization failures (OAuth, tokens, RLS)."""
    pass


class ConfigError(MeridianError):
    """Raised for missing or invalid configuration."""
    pass
