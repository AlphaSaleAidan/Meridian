"""
Webhook Management Routes — Register, list, and manage outbound webhooks.

  POST   /api/webhooks/register     → Register a new webhook
  GET    /api/webhooks/list         → List registered webhooks
  DELETE /api/webhooks/{id}         → Delete a webhook
  GET    /api/webhooks/deliveries   → List recent delivery attempts
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger("meridian.api.webhook_mgmt")

router = APIRouter(prefix="/api/webhooks", tags=["webhook-management"])


class RegisterRequest(BaseModel):
    org_id: str
    url: str
    events: list[str]
    secret: str | None = None


@router.post("/register")
async def register_webhook(body: RegisterRequest):
    """Register an outbound webhook endpoint."""
    from ...db import get_db
    from ...webhooks.registry import register_webhook as do_register

    db = get_db()
    result = await do_register(
        db=db,
        org_id=body.org_id,
        url=body.url,
        events=body.events,
        secret=body.secret,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/list")
async def list_webhooks(org_id: str = Query(...)):
    """List all registered webhooks for an organization."""
    from ...db import get_db
    from ...webhooks.registry import list_webhooks as do_list

    db = get_db()
    return await do_list(db, org_id)


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str, org_id: str = Query(...)):
    """Delete a webhook registration."""
    from ...db import get_db
    from ...webhooks.registry import delete_webhook as do_delete

    db = get_db()
    return await do_delete(db, org_id, webhook_id)


@router.get("/deliveries")
async def list_deliveries(org_id: str = Query(...), limit: int = Query(50, le=200)):
    """List recent webhook delivery attempts."""
    from ...db import get_db
    from ...webhooks.registry import list_deliveries as do_list

    db = get_db()
    return await do_list(db, org_id, limit=limit)
