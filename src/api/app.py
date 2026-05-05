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
try:
    from .routes.billing import router as billing_router
    _has_billing = True
except ImportError:
    _has_billing = False

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
    yield
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
if _has_billing:
    app.include_router(billing_router)


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
