"""
Menu ingestion API — three of the four paths into the menu store.

  POST /api/menu/{merchant_id}/scrape   {url}  → website scrape (LLM extract)
  POST /api/menu/{merchant_id}/csv      (multipart, template format)
  GET  /api/menu/csv-template                  → downloadable template
  POST /api/menu/{merchant_id}/photo    (multipart image → vision/OCR)

The fourth path — POS import — stays at POST /api/phone/menu/sync/{merchant_id}
(phone_dashboard.py), now writing through the store with source='pos'.

Review gate: everything here lands published=false + needs_review=true via
menu_store.ingest_items — a menu that quotes wrong prices is worse than no
menu, so nothing scraped/uploaded goes live until the merchant confirms it
on the review screen. Failures return a clear 4xx — never partial-silent.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ..auth import enforce_service_member, require_service_auth
from ...db import get_db
from ...services import menu_store
from ...services.menu_ingestion import (
    CSV_TEMPLATE,
    MenuIngestError,
    extract_menu_from_photo,
    parse_menu_csv,
)
from .phone_dashboard import _validate_merchant_id

logger = logging.getLogger("meridian.api.menu_ingest")

router = APIRouter(prefix="/api/menu", tags=["menu-ingest"])

_MAX_CSV_BYTES = 1 * 1024 * 1024
_MAX_PHOTO_BYTES = 12 * 1024 * 1024


class ScrapeRequest(BaseModel):
    url: str


async def _authorize(principal, merchant_id: str) -> None:
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)


@router.get("/csv-template", response_class=PlainTextResponse)
async def get_csv_template():
    """The published CSV template (no auth — it's a static example file)."""
    return PlainTextResponse(
        CSV_TEMPLATE,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="meridian-menu-template.csv"'},
    )


@router.post("/{merchant_id}/scrape")
async def scrape_menu_from_website(merchant_id: str, req: ScrapeRequest,
                                   principal=Depends(require_service_auth)):
    """Scrape the merchant's website for menu items. All results land in the
    review queue — scraped items are NEVER auto-published."""
    from ...services.menu_scraper import MenuScrapeError, scrape_menu

    await _authorize(principal, merchant_id)
    url = (req.url or "").strip()
    if url and "://" not in url:
        url = f"https://{url}"
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    try:
        result = await scrape_menu(url)
    except MenuScrapeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    summary = await menu_store.ingest_items(
        get_db(), merchant_id, result["items"], source="scrape")
    return {
        "ok": True,
        "found": len(result["items"]),
        "pending_review": summary["needs_review"],
        "skipped_existing": summary["skipped_existing"],
        "pages": result["pages"],
        "flags": result["flags"],
        "sample": result["items"][:5],
    }


@router.post("/{merchant_id}/csv")
async def import_menu_csv(merchant_id: str, file: UploadFile = File(...),
                          principal=Depends(require_service_auth)):
    """Template-format CSV import with row-by-row validation. Good rows land
    in the review queue; bad rows come back as {row, error} so the merchant
    can fix exactly the right lines."""
    await _authorize(principal, merchant_id)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(raw) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV too large (max 1 MB)")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=422, detail="could not decode CSV text") from exc

    try:
        items, errors = parse_menu_csv(text)
    except MenuIngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    summary = {"needs_review": 0, "skipped_existing": 0}
    if items:
        summary = await menu_store.ingest_items(get_db(), merchant_id, items, source="csv")
    return {
        "ok": True,
        "found": len(items),
        "pending_review": summary["needs_review"],
        "skipped_existing": summary["skipped_existing"],
        "row_errors": errors,
        "sample": items[:5],
    }


@router.post("/{merchant_id}/photo")
async def import_menu_photo(merchant_id: str, photo: UploadFile = File(...),
                            principal=Depends(require_service_auth)):
    """Photo of a printed menu → vision model (OCR fallback) → review queue."""
    await _authorize(principal, merchant_id)
    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(image_bytes) > _MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="image too large (max 12 MB)")

    try:
        items, engine = await extract_menu_from_photo(
            image_bytes, photo.content_type or "")
    except MenuIngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    summary = {"needs_review": 0, "skipped_existing": 0}
    if items:
        summary = await menu_store.ingest_items(get_db(), merchant_id, items, source="photo")
    return {
        "ok": True,
        "found": len(items),
        "pending_review": summary["needs_review"],
        "skipped_existing": summary["skipped_existing"],
        "engine": engine,
        "sample": items[:5],
    }
