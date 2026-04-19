"""
Meridian Configuration — Environment variables and settings.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    # Manual .env loading fallback
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        for line in _env_path.read_text().strip().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class SquareConfig:
    """Square API configuration."""
    app_id: str = os.getenv("SQUARE_APP_ID", "")
    app_secret: str = os.getenv("SQUARE_APP_SECRET", "")
    access_token: str = os.getenv("SQUARE_ACCESS_TOKEN", "")
    environment: str = os.getenv("SQUARE_ENVIRONMENT", "sandbox")
    webhook_signature_key: str = os.getenv("SQUARE_WEBHOOK_SIGNATURE_KEY", "")

    @property
    def base_url(self) -> str:
        if self.environment == "production":
            return "https://connect.squareup.com"
        return "https://connect.squareupsandbox.com"

    @property
    def oauth_authorize_url(self) -> str:
        # OAuth authorize always goes through production URL
        if self.environment == "production":
            return "https://connect.squareup.com/oauth2/authorize"
        return "https://connect.squareupsandbox.com/oauth2/authorize"


@dataclass(frozen=True)
class SyncConfig:
    """Sync engine configuration."""
    backfill_months: int = int(os.getenv("SQUARE_BACKFILL_MONTHS", "18"))
    incremental_interval_minutes: int = int(os.getenv("SQUARE_INCREMENTAL_INTERVAL_MINUTES", "15"))
    max_requests_per_second: float = float(os.getenv("SQUARE_MAX_REQUESTS_PER_SECOND", "8"))
    batch_request_rate: float = 4.0
    orders_per_page: int = 500
    catalog_per_page: int = 1000


@dataclass(frozen=True)
class AppConfig:
    """Application configuration."""
    redirect_uri: str = os.getenv("SQUARE_REDIRECT_URI", "https://app.meridianpos.ai/api/square/callback")
    webhook_url: str = os.getenv("SQUARE_WEBHOOK_URL", "https://app.meridianpos.ai/api/webhooks/square")
    database_url: str = os.getenv("DATABASE_URL", "")
    host: str = os.getenv("APP_HOST", "0.0.0.0")
    port: int = int(os.getenv("APP_PORT", "8000"))
    debug: bool = os.getenv("APP_DEBUG", "false").lower() == "true"


@dataclass(frozen=True)
class RetryConfig:
    """Retry and error handling configuration."""
    max_retries: int = 5
    backoff_base: float = 1.0
    backoff_multiplier: float = 2.0
    retry_on_status: tuple = (429, 500, 502, 503, 504)
    dead_letter_after: int = 5


# Singleton instances
square = SquareConfig()
sync = SyncConfig()
app = AppConfig()
retry = RetryConfig()

# OAuth scopes — read-only, never write to merchant POS
OAUTH_SCOPES = [
    "MERCHANT_PROFILE_READ",
    "ITEMS_READ",
    "ORDERS_READ",
    "PAYMENTS_READ",
    "INVENTORY_READ",
    "EMPLOYEES_READ",
    "CUSTOMERS_READ",
]
