"""Org-tree management routes.

  POST /api/team/assign  → admin sets a rep's role + manager (validates outrank
                           + cycle; the DB trigger re-checks the cycle
                           independently and its error is surfaced as 400)
  GET  /api/team/tree    → caller's subtree as nested JSON (admin: full forest)
"""
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_jwt
from .. import hierarchy

logger = logging.getLogger("meridian.api.team")

router = APIRouter(prefix="/api/team", tags=["team"])


class AssignRequest(BaseModel):
    rep_id: str
    role: str
    manager_id: str | None = None


@router.post("/assign")
async def assign_role(req: AssignRequest, admin: dict = Depends(hierarchy.require_org_admin)):
    """Set role + manager for a rep. Admin only (role='admin' OR allowlist)."""
    import httpx

    hierarchy.validate_uuid(req.rep_id, "rep_id")
    if req.manager_id is not None:
        hierarchy.validate_uuid(req.manager_id, "manager_id")
        if req.manager_id == req.rep_id:
            raise HTTPException(400, "A rep cannot be their own manager")

    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")

    manager_row = None
    if req.manager_id:
        rows = await hierarchy._service_get(
            {"id": f"eq.{req.manager_id}", "select": hierarchy._HIER_COLS, "limit": "1"}
        )
        if not rows:
            raise HTTPException(404, "Manager not found")
        manager_row = rows[0]

    # Plane A: application-level validation (outrank + cycle) …
    hierarchy.check_assignment(req.role, req.rep_id, manager_row)

    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{supabase_url}/rest/v1/sales_reps?id=eq.{req.rep_id}",
            headers=headers,
            json={"role": req.role, "manager_id": req.manager_id},
        )
    # … Plane B: the DB trigger independently rejects cycles — surface it.
    if resp.status_code not in (200, 204):
        detail = resp.text[:300]
        logger.error("team/assign failed for %s: %s %s", req.rep_id, resp.status_code, detail)
        if "cycle" in detail.lower() or "manager" in detail.lower():
            raise HTTPException(400, "Assignment rejected by hierarchy guard (cycle or invalid manager)")
        raise HTTPException(500, "Could not update rep assignment")

    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        raise HTTPException(404, "Rep not found")
    updated = rows[0]
    logger.info(
        "team/assign: %s -> role=%s manager=%s by %s",
        req.rep_id, req.role, req.manager_id, admin.get("email"),
    )
    return {
        "ok": True,
        "rep_id": req.rep_id,
        "role": updated.get("role", req.role),
        "manager_id": updated.get("manager_id", req.manager_id),
        "path": updated.get("path"),
    }


@router.get("/tree")
async def get_tree(user: dict = Depends(require_jwt)):
    """The caller's org subtree as nested JSON. Admin sees the whole forest."""
    scope = await hierarchy.resolve_scope(user)
    if scope.is_admin:
        reps = await hierarchy._service_get({"select": hierarchy._HIER_COLS, "order": "created_at.asc"})
        return {"tree": hierarchy.build_tree(reps), "viewer": {"role": scope.role, "rep_id": scope.rep_id}}

    if not scope.rep_id:
        return {"tree": [], "viewer": {"role": scope.role, "rep_id": None}}

    if scope.path and scope.role != "sales_rep":
        reps = await hierarchy._fetch_reps_under(scope.path)
    else:
        reps = await hierarchy._service_get(
            {"id": f"eq.{scope.rep_id}", "select": hierarchy._HIER_COLS, "limit": "1"}
        )
    return {
        "tree": hierarchy.build_tree(reps, root_ids={scope.rep_id}),
        "viewer": {"role": scope.role, "rep_id": scope.rep_id},
    }
