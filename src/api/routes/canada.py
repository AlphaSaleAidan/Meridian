"""
Canada-specific Routes — Careers applications and Canada portal endpoints.

  POST /api/canada/careers/apply    → Submit a Canadian sales application
  POST /api/canada/create-customer  → Create Supabase Auth user for a Canada customer
"""
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from .careers import submit_application, CareerApplication

logger = logging.getLogger("meridian.api.canada")

router = APIRouter(prefix="/api/canada", tags=["canada"])


class CreateCustomerRequest(BaseModel):
    email: EmailStr
    password: str
    business_name: str
    contact_name: str
    phone: str | None = None
    vertical: str | None = None
    deal_id: str | None = None
    monthly_price: int = 0
    portal: str = "canada"


@router.post("/create-customer")
async def create_customer(req: CreateCustomerRequest):
    import httpx

    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )

    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    org_id = str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
            },
            json={
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.contact_name,
                    "business_name": req.business_name,
                    "org_id": org_id,
                    "role": "owner",
                    "portal": "canada",
                    "vertical": req.vertical,
                },
            },
        )
        if resp.status_code in (200, 201):
            auth_user_id = resp.json().get("id")
            logger.info(f"Created Canada customer auth user {auth_user_id} for {req.email}")
        elif resp.status_code == 422 and "already been registered" in resp.text.lower():
            logger.info(f"Auth user already exists for {req.email}")
        else:
            logger.error(f"Auth user creation failed: {resp.status_code} {resp.text}")
            raise HTTPException(400, "Could not create customer account")

    return {"ok": True, "org_id": org_id}


@router.post("/careers/apply")
async def submit_career_application(req: CareerApplication):
    return await submit_application(req, country="CA")
