"""
Meridian Configuration — Environment variables and settings.
"""
import os
from dataclasses import dataclass
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


# ─── Base URL Detection ───────────────────────────────────
# Resolves the canonical backend URL from env.
# Priority: APP_BASE_URL > RAILWAY_PUBLIC_DOMAIN > fallback

def _resolve_base_url() -> str:
    """Determine the public-facing backend URL."""
    explicit = os.getenv("APP_BASE_URL", "").rstrip("/")
    if explicit:
        return explicit
    railway = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if railway:
        return f"https://{railway}"
    return "https://meridian.tips"

_BASE_URL = _resolve_base_url()


# ─── Square Configuration ─────────────────────────────────

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
        if self.environment == "production":
            return "https://connect.squareup.com/oauth2/authorize"
        return "https://connect.squareupsandbox.com/oauth2/authorize"


# ─── Clover Configuration ─────────────────────────────────

@dataclass(frozen=True)
class CloverConfig:
    """Clover API configuration."""
    app_id: str = os.getenv("CLOVER_APP_ID", "")
    app_secret: str = os.getenv("CLOVER_APP_SECRET", "")
    access_token: str = os.getenv("CLOVER_ACCESS_TOKEN", "")
    merchant_id: str = os.getenv("CLOVER_MERCHANT_ID", "")
    environment: str = os.getenv("CLOVER_ENVIRONMENT", "sandbox")

    @property
    def base_url(self) -> str:
        if self.environment == "production":
            return "https://www.clover.com"
        return "https://sandbox.dev.clover.com"

    @property
    def api_base_url(self) -> str:
        if self.environment == "production":
            return "https://api.clover.com"
        return "https://apisandbox.dev.clover.com"

    @property
    def oauth_authorize_url(self) -> str:
        return f"{self.base_url}/oauth/authorize"

    @property
    def redirect_uri(self) -> str:
        return os.getenv(
            "CLOVER_REDIRECT_URI",
            f"{_BASE_URL}/api/clover/callback",
        )


# ─── Toast Configuration ─────────────────────────────────

@dataclass(frozen=True)
class ToastConfig:
    """Toast API configuration (client_credentials auth)."""
    client_id: str = os.getenv("TOAST_CLIENT_ID", "")
    client_secret: str = os.getenv("TOAST_CLIENT_SECRET", "")
    environment: str = os.getenv("TOAST_ENVIRONMENT", "sandbox")

    @property
    def auth_url(self) -> str:
        return "https://authentication.toasttab.com/authentication/v1/authentication/login"

    @property
    def api_base_url(self) -> str:
        return "https://ws-api.toasttab.com"


# ─── Sync Configuration ───────────────────────────────────

@dataclass(frozen=True)
class SyncConfig:
    """Sync engine configuration (shared across POS integrations)."""
    backfill_months: int = int(os.getenv("SYNC_BACKFILL_MONTHS", "18"))
    incremental_interval_minutes: int = int(os.getenv("SYNC_INCREMENTAL_INTERVAL_MINUTES", "15"))
    max_requests_per_second: float = float(os.getenv("SYNC_MAX_REQUESTS_PER_SECOND", "8"))
    batch_request_rate: float = 4.0
    orders_per_page: int = 500
    catalog_per_page: int = 1000


# ─── App Configuration ────────────────────────────────────

@dataclass(frozen=True)
class AppConfig:
    """Application configuration."""
    redirect_uri: str = os.getenv("SQUARE_REDIRECT_URI", f"{_BASE_URL}/api/square/callback")
    webhook_url: str = os.getenv("SQUARE_WEBHOOK_URL", f"{_BASE_URL}/api/webhooks/square")
    clover_redirect_uri: str = os.getenv("CLOVER_REDIRECT_URI", f"{_BASE_URL}/api/clover/callback")
    clover_webhook_url: str = os.getenv("CLOVER_WEBHOOK_URL", f"{_BASE_URL}/api/webhooks/clover")
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
clover = CloverConfig()
toast = ToastConfig()
sync = SyncConfig()
app = AppConfig()
retry = RetryConfig()

# Square OAuth scopes — read-only, never write to merchant POS
OAUTH_SCOPES = [
    "MERCHANT_PROFILE_READ",
    "ITEMS_READ",
    "ORDERS_READ",
    "PAYMENTS_READ",
    "INVENTORY_READ",
    "EMPLOYEES_READ",
    "CUSTOMERS_READ",
]
