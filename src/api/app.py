"""
Meridian API Server — FastAPI application.

Routes:
  GET  /health                        → Health check
  GET  /api/square/authorize          → Start OAuth flow
  GET  /api/square/callback           → OAuth callback
  POST /api/webhooks/square           → Square webhook receiver
  GET  /api/dashboard/*               → Dashboard data endpoints
  */api/vision/*                      → Vision intelligence endpoints
  POST /api/billing/create-checkout   → Create Square payment link
  POST /api/billing/create-invoice    → Create Square invoice
  GET  /api/billing/status/:org_id    → Subscription status
"""
import logging
import os
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
from .routes.oauth import router as oauth_router
from .routes.webhooks import router as webhook_router
from .routes.dashboard import router as dashboard_router
from .routes.payouts import router as payouts_router
from .routes.onboarding import router as onboarding_router
from .routes.predictive import router as predictive_router
from .routes.admin import router as admin_router
from .routes.vision import router as vision_router
from .routes.cline import router as cline_router
from .routes.pos import router as pos_router
from .routes.spaces import router as spaces_router
from .routes.canada import router as canada_router
from .routes.careers import router as careers_router
from .routes.training import router as training_router
from .routes.email import router as email_api_router
from ..email.webhooks import router as email_webhook_router
from .routes.phone import router as phone_router
from .routes.pos_connections import router as pos_connections_router
from .routes.inference import router as inference_router
from .routes.website import router as website_router
from .routes.schedule import router as schedule_router
from .routes.garry import router as garry_router
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle — initializes DB connection."""
    from ..db import init_db, close_db
    logger.info("Meridian server starting...")
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
        from ..ai.swarm_trainer import get_swarm_trainer
        trainer = get_swarm_trainer(db=_db_instance)
        interval = int(os.environ.get("SWARM_TRAINING_INTERVAL", "300"))
        _trainer_task = asyncio.create_task(trainer.start_autonomous(interval))
        logger.info(f"Autonomous swarm trainer started (every {interval}s)")

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

    yield

    if _trainer_task:
        from ..ai.swarm_trainer import get_swarm_trainer
        get_swarm_trainer().stop()
        _trainer_task.cancel()
        logger.info("Autonomous swarm trainer stopped")
    if _pos_scheduler_started:
        from ..services.pos_scheduler import stop_scheduler
        stop_scheduler()
    await close_db()
    logger.info("Meridian server shut down.")


app = FastAPI(
    title="Meridian",
    description="AI-Powered POS Analytics Platform",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — allow the frontend origins
_allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://app.meridianpos.ai",
    "https://meridian-dashboard.vercel.app",
    "https://meridian-dun-nu.vercel.app",
    "https://meridian-app-c9cd32f1.viktor.space",
    "https://industrious-rabbit-343.convex.site",
    "https://meridian.tips",
    "https://www.meridian.tips",
]

# Allow custom origin from env (e.g. Vercel preview deploys)
_extra_origin = os.environ.get("FRONTEND_ORIGIN")
if _extra_origin:
    _allowed_origins.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(oauth_router)
app.include_router(webhook_router)
app.include_router(dashboard_router)
app.include_router(payouts_router)
app.include_router(onboarding_router)
app.include_router(predictive_router)
app.include_router(admin_router)
app.include_router(vision_router)
app.include_router(cline_router)
app.include_router(pos_router)
app.include_router(spaces_router)
app.include_router(canada_router)
app.include_router(careers_router)
app.include_router(training_router)
app.include_router(email_api_router)
app.include_router(email_webhook_router)
app.include_router(phone_router)
app.include_router(pos_connections_router)
app.include_router(inference_router)
app.include_router(website_router)
app.include_router(schedule_router)
app.include_router(garry_router)
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
