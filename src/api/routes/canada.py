"""
Canada-specific Routes — Careers applications and Canada portal endpoints.

  POST /api/canada/careers/apply  → Submit a Canadian sales application
"""
import logging

from fastapi import APIRouter

from .careers import submit_application, CareerApplication

logger = logging.getLogger("meridian.api.canada")

router = APIRouter(prefix="/api/canada", tags=["canada"])


@router.post("/careers/apply")
async def submit_career_application(req: CareerApplication):
    return await submit_application(req, country="CA")
