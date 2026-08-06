"""
Meridian API Server — FastAPI application.

Routes:
  GET  /health                        → Health check
  GET  /api/square/authorize          → Start OAuth flow
  GET  /api/square/callback           → OAuth callback
  POST /api/webhooks/square           → Square webhook receiver
  GET  /api/dashboard/*               → Dashboard data endpoints
  */api/vision/*                      → Vision intelligence endpoints
  POST /api/billing/create-invoice    → Create Square invoice
  GET  /api/billing/status/:org_id    → Subscription status
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# ── Sentry error tracking (must init before FastAPI) ──
try:
    import sentry_sdk
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN", ""),
        traces_sample_rate=0.2,
        environment=os.getenv("ENVIRONMENT", "production"),
        send_default_pii=False,
    )
except ImportError:
    pass

# ── PostHog analytics (optional) ──
try:
    from posthog import Posthog
    posthog_client = Posthog(
        project_api_key=os.getenv("POSTHOG_API_KEY", ""),
        host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
        disabled=not os.getenv("POSTHOG_API_KEY"),
    )
except ImportError:
    posthog_client = None

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .middleware.rate_limiter import RateLimitMiddleware
from .routes.oauth import router as oauth_router
from .routes.clover_oauth import router as clover_oauth_router
from .routes.clover_hco import router as clover_hco_router
from .routes.pos_connect import router as pos_connect_router
from .routes.webhooks import router as webhook_router
from .routes.dashboard import router as dashboard_router
from .routes.cpa import router as cpa_router
from .routes.payouts import router as payouts_router
from .routes.onboarding import router as onboarding_router
from .routes.predictive import router as predictive_router
from .routes.admin import router as admin_router
from .routes.vision import router as vision_router
from .routes.vision_ingest import router as vision_ingest_router
from .routes.browser_camera import router as browser_camera_router
from .routes.camera_connect import router as camera_connect_router
from .routes.cline import router as cline_router
from .routes.pos import router as pos_router
from .routes.spaces import router as spaces_router
from .routes.canada import router as canada_router
from .routes.commissions import router as commissions_router
from .routes.us import router as us_router
from .routes.compliance import router as compliance_router
from .routes.careers import router as careers_router
from .routes.careers_pipeline import router as careers_pipeline_router
from .routes.team import router as team_router
from .routes.leaderboard import router as leaderboard_router
from .routes.training import router as training_router
from .routes.email import router as email_api_router
from ..email.webhooks import router as email_webhook_router
from .routes.phone import router as phone_router
from .routes.phone_activation import router as phone_activation_router
from .routes.phone_dashboard import router as phone_dashboard_router
from .routes.phone_test_order import router as phone_test_order_router
from .routes.menu import router as menu_router
from .routes.menu_ingest import router as menu_ingest_router
from .routes.stripe_connect import router as stripe_connect_router
from .routes.stripe_checkout import router as stripe_checkout_router
from .routes.pay_redirect import router as pay_redirect_router
from .routes.vapi_webhook import router as vapi_router
from .routes.sms import router as sms_router
from .routes.credits import router as credits_router
from .routes.pos_connections import router as pos_connections_router
from .routes.inference import router as inference_router
from .routes.website import router as website_router
from .routes.schedule import router as schedule_router
from .routes.garry import router as garry_router
from .routes.garry_patches import router as garry_patches_router
from .routes.archives import router as archives_router
from .routes.intelligence import router as intelligence_router
from .routes.inventory_docs import router as inventory_docs_router
from .routes.analytics import router as analytics_router
from .routes.content import router as content_router
from .routes.portal import router as portal_router
from .routes.quote import router as quote_router
from .routes.settings import router as settings_router
from .routes.team_admin import router as team_admin_router
from .routes.time_clock import router as time_clock_router
from .routes.team_chat import router as team_chat_router
from .routes.chatbot import router as chatbot_router
from .routes.hub import router as hub_router
try:
    from .routes.billing import router as billing_router
    _has_billing = True
except ImportError:
    _has_billing = False
try:
    from marketplace.webhook import router as marketplace_router
    _has_marketplace = True
except ImportError:
    _has_marketplace = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-5s | %(message)s",
)

logger = logging.getLogger("meridian")


def _assert_single_worker() -> None:
    """Live call/SMS/card state lives in per-process dicts (phone._sessions,
    sms_order._sms_sessions, card_on_phone._captures). With one uvicorn worker
    (the Procfile today) that is correct; with several, mid-call webhooks land
    on workers that never saw the session and orders/card captures silently
    die. Refuse the foot-gun until that state moves to a shared store —
    MERIDIAN_ALLOW_MULTI_WORKER=1 overrides once it has."""
    if os.environ.get("MERIDIAN_ALLOW_MULTI_WORKER") == "1":
        return
    workers = 0
    try:
        workers = int(os.environ.get("WEB_CONCURRENCY", "0") or 0)
    except ValueError:
        pass
    argv = sys.argv
    for flag in ("--workers", "-w"):
        if flag in argv:
            try:
                workers = max(workers, int(argv[argv.index(flag) + 1]))
            except (IndexError, ValueError):
                pass
    if workers > 1:
        raise RuntimeError(
            f"Refusing to start with {workers} workers: in-memory phone/SMS/card "
            "session state is per-process and breaks under multiple workers. "
            "Move sessions to a shared store first, then set "
            "MERIDIAN_ALLOW_MULTI_WORKER=1."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle — initializes DB connection."""
    from ..db import init_db, close_db
    logger.info("Meridian server starting...")
    _assert_single_worker()
    await init_db()
    logger.info("Database connection initialized")
    from ..payouts.webhook_hook import init_commission_hook
    from ..db import _db_instance
    if _db_instance:
        init_commission_hook(_db_instance)
        logger.info("Commission webhook hook initialized")

    # Start autonomous swarm trainer in background
    import asyncio
    _trainer_task = None
    if os.environ.get("ENABLE_SWARM_TRAINING", "1") == "1":
        try:
            from ..ai.swarm_trainer import get_swarm_trainer
            trainer = get_swarm_trainer(db=_db_instance)
            interval = int(os.environ.get("SWARM_TRAINING_INTERVAL", "300"))
            _trainer_task = asyncio.create_task(trainer.start_autonomous(interval))
            logger.info(f"Autonomous swarm trainer started (every {interval}s)")
        except Exception as e:
            logger.warning(f"Swarm trainer failed to start: {e}")

    # Start POS sync scheduler
    _pos_scheduler_started = False
    if os.environ.get("ENABLE_POS_SYNC", "1") == "1":
        try:
            from ..services.pos_scheduler import start_scheduler
            start_scheduler()
            _pos_scheduler_started = True
            logger.info("POS sync scheduler started")
        except Exception as e:
            logger.warning(f"POS sync scheduler failed to start: {e}")

    # Start training scheduler (6-hour consolidation loop)
    _training_scheduler_started = False
    if os.environ.get("ENABLE_SWARM_TRAINING", "1") == "1":
        try:
            from ..services.training_scheduler import start_training_scheduler
            start_training_scheduler()
            _training_scheduler_started = True
            logger.info("Training scheduler started (6h consolidation)")
        except Exception as e:
            logger.warning(f"Training scheduler failed to start: {e}")

    # Start edge watchdog (probes the Contabo-hosted frontends from Railway)
    _edge_watchdog_started = False
    try:
        from ..services.edge_watchdog import start_edge_watchdog
        _edge_watchdog_started = start_edge_watchdog()
        if _edge_watchdog_started:
            logger.info("Edge watchdog started")
    except Exception as e:
        logger.warning(f"Edge watchdog failed to start: {e}")

    yield

    if _edge_watchdog_started:
        from ..services.edge_watchdog import stop_edge_watchdog
        stop_edge_watchdog()
    if _trainer_task:
        from ..ai.swarm_trainer import get_swarm_trainer
        get_swarm_trainer().stop()
        _trainer_task.cancel()
        logger.info("Autonomous swarm trainer stopped")
    if _training_scheduler_started:
        from ..services.training_scheduler import stop_training_scheduler
        stop_training_scheduler()
    if _pos_scheduler_started:
        from ..services.pos_scheduler import stop_scheduler
        stop_scheduler()
    await close_db()
    logger.info("Meridian server shut down.")


_is_production = os.environ.get("ENVIRONMENT", "production") == "production"

app = FastAPI(
    title="Meridian",
    description="AI-Powered POS Analytics Platform",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# ── CORS — locked to known Meridian domains ──
_allowed_origins = [
    "https://app.meridianpos.ai",
    "https://meridian-dashboard.vercel.app",
    "https://meridian-dun-nu.vercel.app",
    "https://meridian-app-c9cd32f1.viktor.space",
    "https://industrious-rabbit-343.convex.site",
    "https://meridian.tips",
    "https://www.meridian.tips",
    "https://canada.meridian.tips",
]

if not _is_production:
    _allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:5173",
    ])

_extra_origin = os.environ.get("FRONTEND_ORIGIN")
if _extra_origin:
    _allowed_origins.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=3600,
)

# ── Security middleware (reverse order: last added = outermost = runs first) ──
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# Register API routes
app.include_router(oauth_router)
app.include_router(clover_oauth_router)
app.include_router(clover_hco_router)
app.include_router(pos_connect_router)
app.include_router(webhook_router)
app.include_router(dashboard_router)
app.include_router(cpa_router)
app.include_router(payouts_router)
app.include_router(onboarding_router)
app.include_router(predictive_router)
app.include_router(admin_router)
app.include_router(vision_router)
app.include_router(vision_ingest_router)
app.include_router(browser_camera_router)
app.include_router(camera_connect_router)
app.include_router(cline_router)
app.include_router(pos_router)
app.include_router(spaces_router)
app.include_router(canada_router)
app.include_router(commissions_router)  # rep-facing READ-ONLY commission engine (mig 045)
app.include_router(us_router)
app.include_router(compliance_router)
app.include_router(careers_router)
app.include_router(careers_pipeline_router)
app.include_router(team_router)
app.include_router(leaderboard_router)
app.include_router(training_router)
app.include_router(email_api_router)
app.include_router(email_webhook_router)
app.include_router(phone_router)
app.include_router(phone_activation_router)
app.include_router(phone_dashboard_router)
app.include_router(phone_test_order_router)
app.include_router(menu_router)
app.include_router(menu_ingest_router)
app.include_router(stripe_connect_router)
app.include_router(stripe_checkout_router)
app.include_router(pay_redirect_router)
app.include_router(vapi_router)
app.include_router(sms_router)
app.include_router(credits_router)
app.include_router(pos_connections_router)
app.include_router(inference_router)
app.include_router(website_router)
app.include_router(schedule_router)
app.include_router(garry_router)
app.include_router(garry_patches_router)
app.include_router(archives_router)
app.include_router(intelligence_router)
app.include_router(inventory_docs_router)
app.include_router(analytics_router)
app.include_router(content_router)
app.include_router(portal_router)
app.include_router(quote_router)
app.include_router(settings_router)
# Team Management (Workstream 1): employee RBAC admin, time clock, internal chat,
# customer chatbot. All org-scoped + server-side permission enforced (src/api/rbac.py).
app.include_router(team_admin_router)
app.include_router(time_clock_router)
app.include_router(team_chat_router)
app.include_router(chatbot_router)
app.include_router(hub_router)
if _has_billing:
    app.include_router(billing_router)
if _has_marketplace:
    app.include_router(marketplace_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    from ..db import _db_instance
    db_status = "connected" if _db_instance else "not_initialized"
    return {
        "status": "healthy",
        "service": "meridian",
        "version": "0.2.0",
        "database": db_status,
    }
