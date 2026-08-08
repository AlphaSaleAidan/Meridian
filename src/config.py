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

# Clover runs separate production hosts per region; a merchant's tokens + data
# live ONLY on their region's host. "na" (US + Canada) is the default. Sandbox is
# region-agnostic, so these only apply in production.
_CLOVER_PROD_WEB = {
    "na": "https://www.clover.com",
    "eu": "https://eu.clover.com",
    "la": "https://la.clover.com",
}
_CLOVER_PROD_API = {
    "na": "https://api.clover.com",
    "eu": "https://api.eu.clover.com",
    "la": "https://api.la.clover.com",
}


@dataclass(frozen=True)
class CloverConfig:
    """Clover API configuration."""
    app_id: str = os.getenv("CLOVER_APP_ID", "")
    app_secret: str = os.getenv("CLOVER_APP_SECRET", "")
    access_token: str = os.getenv("CLOVER_ACCESS_TOKEN", "")
    merchant_id: str = os.getenv("CLOVER_MERCHANT_ID", "")
    # Clover Auth Code (Dashboard → Your Apps → App Settings → Webhooks). Merchant
    # webhooks carry it verbatim in the X-Clover-Auth header; we authenticate by
    # comparing, NOT by HMAC. https://docs.clover.com/dev/docs/webhooks
    webhook_auth_code: str = os.getenv("CLOVER_WEBHOOK_AUTH_CODE", "")
    environment: str = os.getenv("CLOVER_ENVIRONMENT", "sandbox")
    region: str = os.getenv("CLOVER_REGION", "na").lower()
    # Built but gated: connector exists, but new connect/test attempts return
    # "coming soon" until POS_CLOVER_ENABLED=true. Square is the live provider.
    enabled: bool = os.getenv("POS_CLOVER_ENABLED", "false").lower() == "true"

    @property
    def has_oauth_credentials(self) -> bool:
        """1-click OAuth genuinely requires BOTH the server-side app id+secret."""
        return bool(self.app_id and self.app_secret)

    @property
    def has_credentials(self) -> bool:
        """Any Clover credential configured server-side (OAuth app, static token,
        merchant id, or webhook auth code)."""
        return bool(
            self.app_id or self.app_secret or self.access_token
            or self.merchant_id or self.webhook_auth_code
        )

    @property
    def is_enabled(self) -> bool:
        """Single coherent gate for whether this server offers Clover as a POS
        provider. True when explicitly enabled via POS_CLOVER_ENABLED, OR when
        any Clover credential is configured — mirroring Square, which is simply
        "on" once its credentials exist. Every Clover entry point (OAuth connect,
        manual connect, test-connection, webhook) reads this so they behave
        consistently: configured → works end-to-end; unconfigured → fails the
        same way everywhere instead of 503-on-OAuth / open-on-manual-connect.
        """
        return self.enabled or self.has_credentials

    @property
    def base_url(self) -> str:
        if self.environment == "production":
            return _CLOVER_PROD_WEB.get(self.region, _CLOVER_PROD_WEB["na"])
        return "https://sandbox.dev.clover.com"

    @property
    def api_base_url(self) -> str:
        if self.environment == "production":
            return _CLOVER_PROD_API.get(self.region, _CLOVER_PROD_API["na"])
        return "https://apisandbox.dev.clover.com"

    @property
    def oauth_authorize_url(self) -> str:
        return f"{self.base_url}/oauth/authorize"

    # v2/OAuth expiring-token endpoints. Production lives on the regional web host
    # (e.g. www.clover.com); sandbox lives on the API host (apisandbox.dev.clover.com),
    # NOT the sandbox web host. https://docs.clover.com/dev/docs/use-oauth
    @property
    def _oauth_v2_host(self) -> str:
        return self.base_url if self.environment == "production" else self.api_base_url

    @property
    def oauth_v2_token_url(self) -> str:
        return f"{self._oauth_v2_host}/oauth/v2/token"

    @property
    def oauth_v2_refresh_url(self) -> str:
        return f"{self._oauth_v2_host}/oauth/v2/refresh"

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
    # Square HMAC verification must use the exact notification URL Square
    # signs against; str(request.url) reconstructs the internal/http URL
    # behind Railway's TLS-terminating proxy and always mismatches.
    billing_webhook_url: str = os.getenv("BILLING_WEBHOOK_URL", f"{_BASE_URL}/api/billing/webhook")
    credits_webhook_url: str = os.getenv("CREDITS_WEBHOOK_URL", f"{_BASE_URL}/api/credits/webhook/square")
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


# ─── DeepSeek — one default for every service EXCEPT the phone agent ────
# Three call sites used to hardcode the URL and model inline, so a global
# override silently missed them. They read these instead now.
#
# services/phone_agent deliberately runs deepseek-v4-flash for low latency and
# tool-calling on live calls, and reads PHONE_DEEPSEEK_MODEL — so pointing
# DEEPSEEK_MODEL at the cheaper V3 chat model never drags the voice path back.
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


# ─── AI Feature Flags ───────────────────────────────────
# LLM insight enhancement defaults OFF and has no consumer here: the only
# reader is src/ai/engine.py, which reads the env directly and also defaults
# off. This declaration used to default "1" under an "all default ON" heading,
# which read as if the layer were live in production — it is not, because
# DeepSeek rejects the JSON mode enhance_insights requires and the OpenAI
# fallback is out of quota (docs/known_issues.md §1). Kept in sync so the
# declared default matches the effective one; flip both once §1 is fixed.
ENABLE_LLM_INSIGHTS: bool = os.getenv("ENABLE_LLM_INSIGHTS", "").lower() in ("1", "true")
ENABLE_REASONING: bool = os.getenv("MERIDIAN_REASONING", "1") == "1"
ENABLE_SWARM_TRAINING: bool = os.getenv("ENABLE_SWARM_TRAINING", "1").lower() in ("1", "true")
ENABLE_CANADA_INTELLIGENCE: bool = os.getenv("ENABLE_CANADA_INTELLIGENCE", "1").lower() in ("1", "true")
ENABLE_FINANCIAL_INTELLIGENCE: bool = os.getenv("ENABLE_FINANCIAL_INTELLIGENCE", "1").lower() in ("1", "true")
