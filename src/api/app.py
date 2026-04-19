"""
Meridian API Server — FastAPI application.

Routes:
  GET  /health                    → Health check
  GET  /api/square/authorize      → Start OAuth flow
  GET  /api/square/callback       → OAuth callback
  POST /api/webhooks/square       → Square webhook receiver
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.oauth import router as oauth_router
from .routes.webhooks import router as webhook_router
from ..config import app as app_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-5s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logging.getLogger("meridian").info("Meridian integration server starting...")
    yield
    logging.getLogger("meridian").info("Meridian integration server shutting down...")


app = FastAPI(
    title="Meridian",
    description="AI-Powered POS Analytics Platform — Square Integration Server",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — enumerate methods explicitly (avoid allow_methods=["*"] with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://app.meridianpos.ai",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register routes
app.include_router(oauth_router)
app.include_router(webhook_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "meridian-integration",
        "version": "0.1.0",
    }
