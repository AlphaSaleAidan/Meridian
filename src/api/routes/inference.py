"""Inference API — local LLM, smart routing, vector search, and system stats."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/inference", tags=["inference"])


class InferenceRequest(BaseModel):
    prompt: str
    system: Optional[str] = "You are a helpful business analytics assistant."
    max_tokens: int = 1024
    temperature: float = 0.7
    target: Optional[str] = "auto"
    source: str = "api"


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    source_filter: Optional[str] = None
    tag_filter: Optional[str] = None


@router.post("/generate")
async def generate(req: InferenceRequest):
    from src.inference.router import route_inference, InferenceTarget

    target_map = {
        "auto": InferenceTarget.AUTO,
        "local": InferenceTarget.LOCAL,
        "openai": InferenceTarget.OPENAI,
    }
    target = target_map.get(req.target, InferenceTarget.AUTO)

    result = await route_inference(
        prompt=req.prompt,
        system=req.system,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
        source=req.source,
        target=target,
    )
    return result


@router.post("/search")
async def vector_search(req: SearchRequest):
    from src.inference.embeddings import search
    results = search(
        query=req.query,
        limit=req.limit,
        source_filter=req.source_filter,
        tag_filter=req.tag_filter,
    )
    return {"results": results, "count": len(results)}


@router.get("/stats")
async def inference_stats():
    from src.inference.embeddings import stats
    from pathlib import Path

    model_dir = Path(__file__).parent.parent.parent.parent / "data" / "models"
    models = []
    if model_dir.exists():
        for f in model_dir.glob("*.gguf"):
            models.append({
                "name": f.name,
                "size_gb": round(f.stat().st_size / 1024**3, 2),
            })

    vector_stats = stats()
    return {
        "models": models,
        "vector_store": vector_stats,
        "routing": {
            "default": "local (Qwen 2.5 7B, zero cost)",
            "fallback": "openai api (only if local fails)",
        },
    }


@router.post("/ingest")
async def trigger_ingestion():
    from src.workers.celery_app import celery_app
    task = celery_app.send_task(
        "src.workers.tasks.ingest_scraped_data",
        queue="analysis",
    )
    return {"status": "dispatched", "task_id": task.id}
