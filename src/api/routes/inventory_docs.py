"""
Inventory Document Processing API Routes.

Endpoints:
  GET  /api/inventory-docs/{org_id}              -> List uploaded docs
  POST /api/inventory-docs/{org_id}/process/{id} -> Trigger AI processing
  GET  /api/inventory-docs/{org_id}/status/{id}  -> Check processing status
"""
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from ..auth import require_org_access

logger = logging.getLogger("meridian.api.inventory_docs")

router = APIRouter(prefix="/api/inventory-docs", tags=["inventory-docs"], dependencies=[Depends(require_org_access)])


@router.get("/{org_id}")
async def list_docs(org_id: str):
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    docs = await db.select(
        "inventory_document_uploads",
        filters={"org_id": f"eq.{org_id}"},
    )
    return {"documents": docs or []}


@router.post("/{org_id}/process/{doc_id}")
async def process_doc(org_id: str, doc_id: str, background_tasks: BackgroundTasks):
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    docs = await db.select(
        "inventory_document_uploads",
        filters={"id": f"eq.{doc_id}", "org_id": f"eq.{org_id}"},
        limit=1,
    )
    if not docs:
        raise HTTPException(404, "Document not found")

    doc = docs[0]
    if doc["status"] == "processing":
        return {"message": "Already processing", "status": "processing"}

    await db.update(
        "inventory_document_uploads",
        {"status": "processing"},
        filters={"id": f"eq.{doc_id}"},
    )

    background_tasks.add_task(_process_inventory_doc, org_id, doc)
    return {"message": "Processing started", "status": "processing"}


@router.get("/{org_id}/status/{doc_id}")
async def doc_status(org_id: str, doc_id: str):
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    docs = await db.select(
        "inventory_document_uploads",
        filters={"id": f"eq.{doc_id}", "org_id": f"eq.{org_id}"},
        limit=1,
    )
    if not docs:
        raise HTTPException(404, "Document not found")

    doc = docs[0]
    return {
        "status": doc["status"],
        "extracted_data": doc.get("extracted_data"),
        "error_message": doc.get("error_message"),
        "processed_at": doc.get("processed_at"),
    }


async def _process_inventory_doc(org_id: str, doc: dict):
    """Background: download doc from storage, run AI extraction, store results."""
    from ...db import get_db
    db = get_db()
    doc_id = doc["id"]

    try:
        import httpx

        supabase_url = os.environ.get("SUPABASE_URL", "")
        supabase_key = (
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
            or os.environ.get("SUPABASE_SERVICE_KEY", "")
        )

        if not supabase_url or not supabase_key:
            raise RuntimeError("Supabase credentials not configured")

        file_path = doc["file_path"]
        async with httpx.AsyncClient(timeout=30.0) as http:
            storage_url = f"{supabase_url}/storage/v1/object/inventory-docs/{file_path}"
            resp = await http.get(
                storage_url,
                headers={"Authorization": f"Bearer {supabase_key}", "apikey": supabase_key},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to download file: {resp.status_code}")
            file_bytes = resp.content

        file_type = doc.get("file_type", "")
        extracted = await _extract_with_ai(file_bytes, file_type, doc["file_name"])

        if extracted and extracted.get("items"):
            products = []
            for item in extracted["items"]:
                products.append({
                    "org_id": org_id,
                    "name": item.get("name", "Unknown"),
                    "category": item.get("category"),
                    "cost_per_unit": item.get("cost"),
                    "selling_price": item.get("selling_price"),
                    "supplier": item.get("supplier"),
                    "unit": item.get("unit", "each"),
                    "source": "document_upload",
                })
            if products:
                await db.batch_upsert("products", products, on_conflict="org_id,name")

        await db.update(
            "inventory_document_uploads",
            {
                "status": "completed",
                "extracted_data": extracted,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
            filters={"id": f"eq.{doc_id}"},
        )
        logger.info(f"Inventory doc processed for org={org_id}: {len(extracted.get('items', []))} items extracted")

    except Exception as e:
        logger.error(f"Inventory doc processing failed for org={org_id}: {e}", exc_info=True)
        await db.update(
            "inventory_document_uploads",
            {"status": "failed", "error_message": str(e)[:500]},
            filters={"id": f"eq.{doc_id}"},
        )


async def _extract_with_ai(file_bytes: bytes, file_type: str, file_name: str) -> dict:
    """Use DeepSeek or local LLM to extract structured inventory data from a document."""
    import httpx
    import base64
    import json

    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not deepseek_key:
        return {"items": [], "error": "No AI API key configured"}

    is_image = file_type.startswith("image/")

    if is_image:
        b64 = base64.b64encode(file_bytes).decode()
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an inventory extraction bot. Extract product/item data from this image "
                    "(invoice, price list, inventory sheet). Return ONLY valid JSON with this structure:\n"
                    '{"items": [{"name": "...", "category": "...", "cost": 0.00, "selling_price": 0.00, '
                    '"supplier": "...", "unit": "each", "quantity": 0}]}\n'
                    "Extract as many items as you can see. Use null for unknown fields."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Extract inventory data from this document: {file_name}"},
                    {"type": "image_url", "image_url": {"url": f"data:{file_type};base64,{b64}"}},
                ],
            },
        ]
    else:
        text_content = file_bytes.decode("utf-8", errors="replace")[:8000]
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an inventory extraction bot. Extract product/item data from this document "
                    "(CSV, text, or structured data). Return ONLY valid JSON with this structure:\n"
                    '{"items": [{"name": "...", "category": "...", "cost": 0.00, "selling_price": 0.00, '
                    '"supplier": "...", "unit": "each", "quantity": 0}]}\n'
                    "Extract as many items as you can find. Use null for unknown fields."
                ),
            },
            {
                "role": "user",
                "content": f"Extract inventory data from this document ({file_name}):\n\n{text_content}",
            },
        ]

    try:
        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": messages, "temperature": 0.1, "max_tokens": 4000},
            )
            if resp.status_code != 200:
                return {"items": [], "error": f"AI API returned {resp.status_code}"}

            content = resp.json()["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

            return json.loads(content)
    except json.JSONDecodeError:
        return {"items": [], "raw_response": content[:2000]}
    except Exception as e:
        return {"items": [], "error": str(e)}
