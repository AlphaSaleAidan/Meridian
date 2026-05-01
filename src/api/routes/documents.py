"""
Document OCR Routes — Scan receipts, invoices, and menus.

  POST /api/documents/scan → Upload image, get structured JSON
"""
import logging
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, File, Query, UploadFile, HTTPException

logger = logging.getLogger("meridian.api.documents")

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/scan")
async def scan_document(
    file: UploadFile = File(...),
    doc_type: str = Query("auto", regex="^(auto|receipt|invoice|menu)$"),
    org_id: Optional[str] = Query(None),
):
    """Scan an uploaded document image and return structured data.

    Supports: receipts, invoices, menu photos.
    Returns: extracted items, prices, totals as JSON.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        if file.content_type not in ("application/pdf", "application/octet-stream"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Upload an image or PDF.",
            )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    suffix = os.path.splitext(file.filename or "doc.png")[1] or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        from ...documents.ocr_service import scan_document as do_scan
        result = await do_scan(tmp_path, doc_type=doc_type)

        if org_id:
            result["org_id"] = org_id

        return result
    finally:
        os.unlink(tmp_path)
