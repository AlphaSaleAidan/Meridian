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


def _to_cents(value) -> int | None:
    """Dollars (float/str, possibly with $ or commas) -> integer cents, or None."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "").strip()
            if not value:
                return None
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return None


@router.get("/{org_id}")
async def list_docs(org_id: str, limit: int = 200, offset: int = 0):
    from ...db import _db_instance as db
    if not db:
        raise HTTPException(503, "Database not available")

    # Bound the query — inventory_document_uploads grows unbounded and each row
    # carries a large extracted_data JSONB, so an all-rows select could OOM the
    # worker. Newest first, paginated.
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    docs = await db.select(
        "inventory_document_uploads",
        filters={"org_id": f"eq.{org_id}"},
        order="created_at.desc",
        limit=limit,
        offset=offset,
    )
    return {"documents": docs or [], "limit": limit, "offset": offset}


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
        filters={"id": f"eq.{doc_id}", "org_id": f"eq.{org_id}"},
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

        # Fail clearly instead of silently "completing" with nothing — e.g. the
        # extractor isn't configured, or couldn't read any line-items.
        if not extracted or (not extracted.get("items") and extracted.get("error")):
            raise RuntimeError(extracted.get("error") if extracted else "Could not read the document")
        if not extracted.get("items"):
            raise RuntimeError("No products with costs were found in that document")

        # Map extracted line-items onto the products catalog. The AI returns
        # dollar amounts (cost / selling_price); the products table stores
        # integer cents in `cost_cents` / `price_cents`. Match invoice items to
        # existing catalog rows by name (case-insensitive) and UPDATE their cost
        # so margins can compute; insert genuinely new items. (The previous
        # version wrote `cost_per_unit`/`selling_price`/`category`/`supplier` —
        # none of which are real `products` columns — so _clean_row stripped
        # everything but {org_id,name} and the cost was silently dropped.)
        matched, inserted, unmatched = 0, 0, []
        matched_by = {"sku": 0, "barcode": 0, "name": 0}
        if extracted and extracted.get("items"):
            existing = await db.get_products(org_id)
            # SKU / UPC are far more reliable than name — match on those first,
            # then fall back to a case-insensitive name match.
            by_sku = {(p.get("sku") or "").strip().lower(): p for p in existing if (p.get("sku") or "").strip()}
            by_barcode = {(p.get("barcode") or "").strip().lower(): p for p in existing if (p.get("barcode") or "").strip()}
            by_name = {(p.get("name") or "").strip().lower(): p for p in existing}

            for item in extracted["items"]:
                name = (item.get("name") or "").strip()
                sku = (str(item.get("sku") or "")).strip()
                upc = (str(item.get("upc") or item.get("barcode") or "")).strip()
                cost_cents = _to_cents(item.get("cost"))
                price_cents = _to_cents(item.get("selling_price"))
                if cost_cents is None and price_cents is None:
                    continue
                if not (name or sku or upc):
                    continue

                match = None
                if sku and sku.lower() in by_sku:
                    match = by_sku[sku.lower()]
                    matched_by["sku"] += 1
                elif upc and upc.lower() in by_barcode:
                    match = by_barcode[upc.lower()]
                    matched_by["barcode"] += 1
                elif name and name.lower() in by_name:
                    match = by_name[name.lower()]
                    matched_by["name"] += 1

                if match:
                    update_fields = {"updated_at": datetime.now(timezone.utc).isoformat()}
                    if cost_cents is not None:
                        update_fields["cost_cents"] = cost_cents
                    # Only fill price if the catalog doesn't already have one.
                    if price_cents is not None and not match.get("price_cents"):
                        update_fields["price_cents"] = price_cents
                    await db.update("products", update_fields, filters={"id": f"eq.{match['id']}"})
                    matched += 1
                else:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    await db.insert("products", {
                        "org_id": org_id,
                        "name": name or sku or upc,
                        "sku": sku,
                        "barcode": upc,
                        "cost_cents": cost_cents,
                        "price_cents": price_cents,
                        "is_active": True,
                        "created_at": now_iso,
                        "updated_at": now_iso,
                    })
                    inserted += 1
                    unmatched.append(name or sku or upc)

        # Record the match outcome so the UI can surface "matched N (by SKU/UPC/
        # name); M items couldn't be matched and were added as new products".
        if isinstance(extracted, dict):
            extracted["_match_summary"] = {
                "matched": matched, "inserted": inserted,
                "matched_by": matched_by, "unmatched_names": unmatched,
            }

        await db.update(
            "inventory_document_uploads",
            {
                "status": "completed",
                "extracted_data": extracted,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
            filters={"id": f"eq.{doc_id}", "org_id": f"eq.{org_id}"},
        )
        logger.info(
            f"Inventory doc processed for org={org_id}: "
            f"{len(extracted.get('items', []))} extracted, {matched} cost-matched, {inserted} new"
        )

    except Exception as e:
        logger.error(f"Inventory doc processing failed for org={org_id}: {e}", exc_info=True)
        await db.update(
            "inventory_document_uploads",
            {"status": "failed", "error_message": str(e)[:500]},
            filters={"id": f"eq.{doc_id}", "org_id": f"eq.{org_id}"},
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
                    '{"items": [{"name": "...", "sku": "...", "upc": "...", "category": "...", "cost": 0.00, "selling_price": 0.00, '
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
                    '{"items": [{"name": "...", "sku": "...", "upc": "...", "category": "...", "cost": 0.00, "selling_price": 0.00, '
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
