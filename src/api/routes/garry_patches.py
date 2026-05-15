"""
Garry Patches API — review, approve, reject, and apply patches proposed by Garry.

  GET  /api/garry/patches              → List patches (filter by status)
  GET  /api/garry/patches/{id}         → Get a single patch with full diff
  POST /api/garry/patches/{id}/approve → Approve a patch
  POST /api/garry/patches/{id}/reject  → Reject a patch
  POST /api/garry/patches/{id}/apply   → Apply an approved patch
  POST /api/garry/patches/apply-all    → Apply all approved patches
"""
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_admin
from ...ai.garry_tools import (
    PATCHES_DIR,
    apply_patch,
    get_patch,
    update_patch,
)

router = APIRouter(prefix="/api/garry/patches", tags=["garry-patches"], dependencies=[Depends(require_admin)])


class ReviewRequest(BaseModel):
    reviewer: str = "admin"


@router.get("")
async def list_patches(status: str = "pending"):
    if not PATCHES_DIR.exists():
        return {"patches": [], "count": 0}

    import json
    patches = []
    for f in sorted(PATCHES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            patch = json.loads(f.read_text())
            if status == "all" or patch.get("status") == status:
                patches.append(patch)
        except Exception:
            continue

    return {"patches": patches, "count": len(patches)}


@router.get("/{patch_id}")
async def get_patch_detail(patch_id: str):
    patch = get_patch(patch_id)
    if not patch:
        raise HTTPException(404, "Patch not found")
    return patch


@router.post("/{patch_id}/approve")
async def approve_patch(patch_id: str, req: ReviewRequest):
    patch = get_patch(patch_id)
    if not patch:
        raise HTTPException(404, "Patch not found")
    if patch["status"] != "pending":
        raise HTTPException(400, f"Patch is already {patch['status']}")

    updated = update_patch(patch_id, {
        "status": "approved",
        "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewed_by": req.reviewer,
    })
    return {"status": "approved", "patch": updated}


@router.post("/{patch_id}/reject")
async def reject_patch(patch_id: str, req: ReviewRequest):
    patch = get_patch(patch_id)
    if not patch:
        raise HTTPException(404, "Patch not found")
    if patch["status"] != "pending":
        raise HTTPException(400, f"Patch is already {patch['status']}")

    updated = update_patch(patch_id, {
        "status": "rejected",
        "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewed_by": req.reviewer,
    })
    return {"status": "rejected", "patch": updated}


@router.post("/{patch_id}/apply")
async def apply_single_patch(patch_id: str):
    result = apply_patch(patch_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/apply-all")
async def apply_all_approved():
    if not PATCHES_DIR.exists():
        return {"applied": 0, "results": []}

    import json
    results = []
    for f in sorted(PATCHES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime):
        try:
            patch = json.loads(f.read_text())
            if patch.get("status") == "approved":
                result = apply_patch(patch["id"])
                results.append(result)
        except Exception:
            continue

    applied = sum(1 for r in results if r.get("status") == "applied")
    return {"applied": applied, "total": len(results), "results": results}
